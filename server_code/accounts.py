import anvil.users
import anvil.server
import anvil.tables
from anvil.tables import app_tables, order_by
import anvil.google.auth
import anvil.tables.query as q
from anvil import secrets
from . import parameters as p
from . import portable as port
from . import server_misc as sm
from .server_misc import authenticated_callable
from anvil_extras.server_utils import timed


@timed
def initialize_session(time_zone):
  """initialize session state: user_id, user, and current_row"""
  user, trust_level = _init_user(time_zone)
  if p.DEBUG_MODE and trust_level >= sm.TEST_TRUST_LEVEL:
    from . import server_auto_test
    server_auto_test.server_auto_tests()
    #anvil.server.launch_background_task('server_auto_tests')
  return user

@timed
def _init_user(time_zone):
  user = anvil.users.get_user()
  print(user['email'])
  _init_user_info_transaction(user, time_zone)
  trust_level = _update_trust_level(user)
  return user, trust_level


@anvil.tables.in_transaction(relaxed=True)
def _init_user_info_transaction(user, time_zone):
  return init_user_info(user, time_zone)


def init_user_info(user, time_zone=""):
  """Return trust, initializing info for new users & updating trust_level"""
  user.update(time_zone=time_zone, init_date=sm.now())
  if user['trust_level'] is None:
    user['notif_settings'] = {"essential": "sms",
                              "message": "email",
                              "email": {"eligible": 1, "eligible_users": [], "eligible_groups": [], "eligible_starred": True},
                              "sms": {"eligible": 0, "eligible_users": [], "eligible_groups": [], "eligible_starred": False},
                             }
    user['first_name'] = ""
    user['last_name'] = ""
    user['how_empathy'] = ""
    user['profile'] = ""
    user['phone'] = ""
    user['profile_url'] = ""


@anvil.tables.in_transaction
def _update_trust_level(user):
  """Return trust level based on other info
  
  Side-effect: update user['trust_level']"""
  def matched_with_distance1_member():
    import connections as c
    for user2 in c.member_close_connections(user):
      user2_matches = app_tables.matches.search(users=[user,user2])
      for match in user2_matches:
        both_present = 1
        for i, u in enumerate(match['users']):
          if u in [user, user2] and match['present'][i] == 0:
            both_present = 0
            break
        if both_present:
          return True
    return False
  trust = user['trust_level']
  if not trust:
    trust = 0
  if trust < 1 and user['confirmed_email']:
    trust = 1 # Guest
  if (trust < 2) and user['phone']: # even if not yet confirmed email
    trust = 2 # Confirmed
  if (trust >= 2 and trust < 3) and matched_with_distance1_member():
    trust = 3 # Member
  if (trust >= 3 and trust < 4) and user['url_confirmed_date'] and user['contributor']:
    trust = 4 # Partner
  if not user['trust_level'] or trust > user['trust_level']:
    user['trust_level'] = trust
  return user['trust_level']

trust_label = {0: "Visitor",
               1: "Guest",
               2: "Confirmed",
               3: "Member",
               4: "Partner",
               10: "Admin",
              }


@anvil.server.callable
def do_signup(email):
  """Returns user (existing user if existing email, else creates new user and sends login email)"""
  user, newly_created = _create_user_if_needed_and_return_whether_created(email)
  if newly_created:
    anvil.users.send_password_reset_email(email) # This can also raise AuthenticationFailed, but shouldn't
  else:
    raise anvil.users.UserExists(f"An account already exists for this email address.")
  return user


@anvil.tables.in_transaction
def _create_user_if_needed_and_return_whether_created(email):
  user = app_tables.users.get(email=email)
  if not user:
    if _email_invalid(email):
      print("Invalid email")
      raise(anvil.users.AuthenticationFailed("Invalid email"))
    all_users = app_tables.users.search()
    for u in all_users:
      if _emails_equal(email, u['email']):
        user = u
  if not user:
    print(f"do_signup adding new user: {email}")
    user = app_tables.users.add_row(email=email, enabled=True, signed_up=sm.now())
    return user, True
  else:
    return user, False

  
def _email_invalid(email):
  import re
  # pattern source: https://stackoverflow.com/revisions/201378/26
  pattern = r"""(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])"""
  return not bool(re.match(pattern, email))
  

def _emails_equal(a, b):
  import re
  em_re = re.compile(r"^([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)$")
  a_match = em_re.search(a)
  b_match = em_re.search(b)
  return a_match.group(1) == b_match.group(1) and a_match.group(2).lower() == b_match.group(2).lower()
  
  
# @anvil.server.callable
# @anvil.tables.in_transaction
# def do_google_signup(email):
#   if anvil.google.auth.get_user_email() == email:
#     user = app_tables.users.get(email=email)
#     if not user:
#       user = app_tables.users.add_row(email=email, enabled=True, signed_up=sm.now())
#       anvil.users.force_login(user)
#     return user


@anvil.server.callable
@anvil.tables.in_transaction(relaxed=True)
def remove_user(user):
  """Remove new user created via Google sign-in"""
  sm.warning(f"Removing user {user['email']}")
  if user and (not user['init_date']):
    user['enabled'] = False

    
def _number_already_taken(number):
  return bool(len(app_tables.users.search(phone=number)))


@authenticated_callable
def send_verification_sms(number, user_id=""):
  if _number_already_taken(number):
    return "number unavailable"
  else:
    user = sm.get_acting_user()
    code = sm.random_code(num_chars=6, digits_only=True)
    from . import notifies as n
    error_message = n.send_sms(
      number,
      f"{code} is your empathy.chat verification code. It expires in 10 minutes.",
    )
    if error_message:
      return error_message
    else:
      app_tables.codes.add_row(
        type="phone",
        address=number,
        code=code,
        user=user,
        date=sm.now()
      )
      return "code sent"
  
  
@authenticated_callable
@anvil.tables.in_transaction
def check_phone_code(code, user_id=""):
  import datetime
  user = sm.get_acting_user(user_id)
  from . import matcher
  matcher.propagate_update_needed()
  # first expunge old codes
  _now = sm.now()
  for code_row in app_tables.codes.search():
    if _now - code_row['date'] > datetime.timedelta(minutes=10):
      code_row.delete()
  current_code_rows = app_tables.codes.search(order_by("date", ascending=False), user=user, type="phone")
  any_failed = False
  if len(current_code_rows) > 0:
    latest_code_row = current_code_rows[0]
    code_matches = code == latest_code_row['code']
    if code_matches:
      user['phone'] = latest_code_row['address']
      any_confirmed, any_failed = _check_for_confirmed_invites(user)
    return code_matches, any_failed
  else:
    return None, any_failed
 

def _check_for_confirmed_invites(user):
  any_confirmed = False
  any_failed = False
  for invite_row in sm.inviteds(user):
    invite_reply = app_tables.invites.get(origin=False, user1=user, link_key=invite_row['link_key'], current=True)
    if invite_reply:
      from . import connections as c
      if c.try_connect(invite_row, invite_reply):
        any_confirmed = True
      else:
        any_failed = True
        from . import invites_server
        sm.add_invite_guess_fail_prompt(invites_server.Invite.from_invite_row(invite_row))
        c.remove_invite_pair(invite_row, invite_reply, user)
    else:
      warning(f"invite_reply not found, {dict(invite_row)}")
  return any_confirmed, any_failed    
    
    
@authenticated_callable
def init_profile(user_id=""):
  from . import connections as c
  from . import relationship as rel
  user = sm.get_other_user(user_id)
  record = c.connection_record(user, sm.get_acting_user())
  relationship = rel.Relationship(distance=record['distance'])
  record.update({'relationships': [] if record['me'] else c.get_relationships(user),
                 'how_empathy': user['how_empathy'],
                 'profile': user['profile'],
                 'profile_updated': user['profile_updated'],
                 'profile_url': user['profile_url'] if relationship.profile_url_visible else "",
                })
  return port.UserProfile(**record)
    
  
@authenticated_callable
def set_seeking_buddy(seeking, user_id=""):
  user = sm.get_acting_user(user_id)
  from . import matcher
  matcher.propagate_update_needed(user)
  user['seeking_buddy'] = seeking
  
  
@authenticated_callable
def save_name(name_item, user_id=""):
  user = sm.get_acting_user(user_id)
  from . import matcher
  matcher.propagate_update_needed(user)
  user['first_name'] = name_item['first']
  user['last_name'] = name_item['last']
  
  
@authenticated_callable
def save_user_field(item_name, value, user_id=""):
  if item_name in ['how_empathy', 'profile']:
    user = sm.get_acting_user(user_id)
    user[item_name] = value
    if item_name == 'profile':
      user['profile_updated'] = sm.now()
  else:
    sm.warning(f"Attempt to use 'save_user_field' for unauthorized item_name: {item_name}")
  

@authenticated_callable
def get_settings(user_id=""):
  """Return user settings displayed on SettingsForm"""
  from . import groups
  user = sm.get_acting_user(user_id)
  item_lists = {}
  item_lists['user_items'], item_lists['group_items'], item_lists['starred_name_list'] = sm.init_create_form(user_id)
  notif_settings = dict(user['notif_settings'])
  elig_items = {}
  for medium in ['sms', 'email']:
    elig_items[medium] = notif_settings.pop(medium) if notif_settings.get(medium) else dict(eligible=0, eligible_starred=False, eligible_users=[], eligible_groups=[])
    elig_items[medium]['eligible_users'] = [sm.get_port_user(sm.get_other_user(u_id), simple=True) for u_id in elig_items[medium]['eligible_users']]
    eligible_group_rows = [app_tables.groups.get_by_id(g_id) for g_id in elig_items[medium]['eligible_groups']]
    elig_items[medium]['eligible_groups'] = [groups.Group(group_row['name'], group_row.get_id()) for group_row in eligible_group_rows]
    elig_items[medium].update(item_lists)
  return (user['phone'], user['time_zone'], notif_settings, elig_items)


@authenticated_callable
@anvil.tables.in_transaction(relaxed=True)
def set_notif_settings(notif_settings, elig_items, user_id=""):
  print(f"set_notif_settings, {notif_settings}")
  from . import groups
  user = sm.get_acting_user(user_id)
  for medium in ['sms', 'email']:
    notif_settings[medium] = {k: elig_items[medium][k] for k in ['eligible', 'eligible_starred']}
    notif_settings[medium]['eligible_users'] = [port_user.user_id for port_user in elig_items[medium]['eligible_users']]
    notif_settings[medium]['eligible_groups'] = [group.group_id for group in elig_items[medium]['eligible_groups']]
  user['notif_settings'] = notif_settings

  
def get_eligibility_specs(user):
  specs = {}
  notif_settings = user['notif_settings']
  for medium in ['sms', 'email']:
    if notif_settings.get(medium):
      specs[medium] = {k: notif_settings[medium][k] for k in ['eligible', 'eligible_starred']}
      specs[medium]['user'] = user
      specs[medium]['eligible_users'] = [sm.get_other_user(u_id) for u_id in notif_settings[medium]['eligible_users']]
      specs[medium]['eligible_groups'] = [app_tables.groups.get_by_id(g_id) for g_id in notif_settings[medium]['eligible_groups']]
  return specs


@authenticated_callable
def get_partner_criteria_info(user_id=""):
  user = sm.get_acting_user(user_id)
  return {'contributor': user['contributor'],
          'profile_url': user['profile_url'],
          'url_confirmed_date': user['url_confirmed_date'],
         }


@authenticated_callable
def submit_url_for_review(url, user_id=""):
  from . import notifies as n
  admin = app_tables.users.get(email=secrets.get_secret('admin_email'))
  user = sm.get_acting_user(user_id)
  user['profile_url'] = url
  email_text = f"{user['first_name']} {user['last_name']} ({user['email']}): {url}"
  n.email_send(admin, "Profile confirmation request", email_text)
  

@authenticated_callable
def submit_contribution_desc(contribution_desc, user_id=""):
  from . import notifies as n
  admin = app_tables.users.get(email=secrets.get_secret('admin_email'))
  user = sm.get_acting_user(user_id)
  email_text = f"{user['first_name']} {user['last_name']} ({user['email']}): {contribution_desc}"
  n.email_send(admin, "Contribution confirmation request", email_text)
  