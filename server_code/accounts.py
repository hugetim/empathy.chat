import anvil.users
import anvil.server
import anvil.tables
from anvil.tables import app_tables, order_by
import anvil.google.auth
import anvil.tables.query as q
from anvil import secrets
from . import parameters as p
from .exceptions import InvalidInviteError
from . import server_misc as sm
from .server_misc import authenticated_callable
from anvil_extras.server_utils import timed
from anvil_extras.logging import TimerLogger


@anvil.server.callable
def get_user(allow_remembered=True, with_id=False):
  if with_id:
    user = anvil.users.get_user(allow_remembered)
    return user, user.get_id() if user else ""
  else:
    return anvil.users.get_user(allow_remembered)

def initialize_session(time_zone, user):
  """initialize session state: user_id, user, and current_row"""
  with TimerLogger("initialize_session", format="{name}: {elapsed:6.3f} s | {msg}") as timer:
    timer.check("anvil.users.get_user")
    starting_trust_level = _init_user_info_transaction(user, time_zone)
    timer.check("_init_user_info_transaction")
    trust_level = _new_trust_level(user, starting_trust_level)
    if trust_level != starting_trust_level:
      user['trust_level'] = trust_level
    return trust_level


@anvil.tables.in_transaction(relaxed=True)
def _init_user_info_transaction(user, time_zone):
  print(f"                    {user['email']}")
  return init_user_info(user, time_zone)


def init_user_info(user, time_zone=""):
  """Return trust, initializing info for new users & updating trust_level"""
  user.update(time_zone=time_zone, init_date=sm.now())
  starting_trust_level = user['trust_level']
  if starting_trust_level is None:
    notif_settings = {
      "essential": "sms",
      "message": "email",
      "email": {"eligible": 1, "eligible_users": [], "eligible_groups": [], "eligible_starred": True},
      "sms": {"eligible": 0, "eligible_users": [], "eligible_groups": [], "eligible_starred": False},
    }
    user.update(notif_settings=notif_settings,
                first_name="", last_name="", how_empathy="", profile="", phone="", profile_url="")
  return starting_trust_level


def _new_trust_level(user, starting_trust_level):
  """Return trust level based on other info"""
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
  trust = starting_trust_level
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
  return starting_trust_level if (starting_trust_level and starting_trust_level >= trust) else trust


trust_label = {0: "Visitor",
               1: "Guest",
               2: "Confirmed",
               3: "Member",
               4: "Partner",
               10: "Admin",
              }


def get_invite_from_port(port_invite):
  from . import invites
  from . import invites_server
  from . import groups
  from . import groups_server
  if isinstance(port_invite, invites.Invite):
    return invites_server.Invite(port_invite)
  if isinstance(port_invite, groups.Invite):
    return groups_server.Invite(port_invite)


@anvil.server.callable
def do_signup(email, port_invite):
  """Returns user (existing user if existing email, else creates new user and sends login email)"""
  invite = get_invite_from_port(port_invite)
  if not invite.authorizes_signup():
    raise InvalidInviteError("Sorry, signup is not authorized by this invite and response.")
  user, newly_created = _create_user_if_needed_and_return_whether_created(email)
  if newly_created:
    anvil.users.send_password_reset_email(email) # This can also raise AuthenticationFailed, but shouldn't
  else:
    raise anvil.users.UserExists(f"An account already exists for this email address.")
  return user


@anvil.tables.in_transaction
def _create_user_if_needed_and_return_whether_created(email):
  user = _get_user_by_email(email)
  if user:
    return user, False
  else:
    print(f"do_signup adding new user: {email}")
    user = app_tables.users.add_row(email=email, enabled=True, signed_up=sm.now())
    return user, True


def _get_user_by_email(email):
  user = app_tables.users.get(email=email)
  if not user:
    if _email_invalid(email):
      print(f"Invalid email: {email}")
      raise anvil.users.AuthenticationFailed("Invalid email")
    all_users = app_tables.users.search()
    for u in all_users:
      if _emails_equal(email, u['email']):
        user = u
  return user

  
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
        address=secrets.encrypt_with_key("new_key", number),
        code=code,
        user=user,
        date=sm.now()
      )
      return "code sent"
  
  
@authenticated_callable
@anvil.tables.in_transaction
def check_phone_code(code, user_id=""):
  import datetime
  from . import matcher
  user = sm.get_acting_user(user_id)
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
  else:
    code_matches = None
  matcher.propagate_update_needed()
  return code_matches, any_failed
 

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
        sm.add_invite_guess_fail_prompt(invites_server.Invite.from_invite_row(invite_row, user=user))
        c.remove_invite_pair(invite_row, invite_reply, user)
    else:
      warning(f"invite_reply not found, {dict(invite_row)}")
  return any_confirmed, any_failed    
      
  
@authenticated_callable
def set_seeking_buddy(seeking, user_id=""):
  from . import matcher
  user = sm.get_acting_user(user_id)
  user['seeking_buddy'] = seeking
  matcher.propagate_update_needed(user)
  
  
@authenticated_callable
def save_name(name_item, user_id=""):
  from . import matcher
  user = sm.get_acting_user(user_id)
  user['first_name'] = name_item['first']
  user['last_name'] = name_item['last']
  matcher.propagate_update_needed(user)
  
  
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
  notif_settings = dict(user['notif_settings'])
  elig_items = {}
  for medium in ['sms', 'email']:
    elig_items[medium] = notif_settings.pop(medium) if notif_settings.get(medium) else dict(eligible=0, eligible_starred=False, eligible_users=[], eligible_groups=[])
    elig_items[medium]['eligible_users'] = [sm.get_port_user(sm.get_other_user(u_id), user1=user, simple=True) for u_id in elig_items[medium]['eligible_users']]
    eligible_group_rows = [app_tables.groups.get_by_id(g_id) for g_id in elig_items[medium]['eligible_groups']]
    elig_items[medium]['eligible_groups'] = [groups.Group(group_row['name'], group_row.get_id()) for group_row in eligible_group_rows]
  time_zone = user['time_zone']
  if not time_zone:
    time_zone = "America/Chicago"
  return (sm.phone(user), time_zone, notif_settings, elig_items)


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
  