import anvil.users
import anvil.server
import anvil.tables
from anvil.tables import app_tables, order_by
import anvil.google.auth
import anvil.tables.query as q
import anvil.secrets
import anvil.email
from . import parameters as p
from . import helper as h
from . import portable as port
from anvil_extras.server_utils import timed


DEBUG = False #p.DEBUG_MODE
TEST_TRUST_LEVEL = 10
authenticated_callable = anvil.server.callable(require_user=True)


def now():
  """Return utcnow"""
  import datetime
  return datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc())


def initialize_session(time_zone):
  """initialize session state: user_id, user, and current_row"""
  user, trust_level = _init_user(time_zone)
  if p.DEBUG_MODE and user['trust_level'] >= TEST_TRUST_LEVEL:
    from . import server_auto_test
    server_auto_test.server_auto_tests()
    #anvil.server.launch_background_task('server_auto_tests')
  return user


def _init_user(time_zone):
  user = anvil.users.get_user()
  print(user['email'])
  _init_user_info_transaction(user, time_zone)
  trust_level = _update_trust_level(user)
  return user, trust_level


@anvil.server.callable
@anvil.tables.in_transaction(relaxed=True)
def remove_user(user):
  """Remove new user created via Google sign-in"""
  h.warning(f"Removing user {user['email']}")
  if user and (not user['init_date']):
    user['enabled'] = False

    
def get_acting_user(user_id="", require_auth=True):
  if DEBUG:
    print("get_acting_user", user_id)
  logged_in_user = anvil.users.get_user()
  if user_id == "" or (logged_in_user and logged_in_user.get_id() == user_id):
    return logged_in_user
  elif (require_auth and (not logged_in_user or logged_in_user['trust_level'] < TEST_TRUST_LEVEL)):
    raise RuntimeError("User not authorized to access this information")
  else:
    return get_other_user(user_id)


def get_other_user(user_id):
  if user_id:
    return app_tables.users.get_by_id(user_id)
  else:
    return anvil.users.get_user()


@anvil.server.callable
def report_error(err_repr, app_info_dict):
  from . import notifies as n
  admin = app_tables.users.get(email="hugetim@gmail.com")
  current_user = anvil.users.get_user()
  if admin != current_user:
    current_user_email = current_user['email'] if current_user else ""
    content = (
      f"""{err_repr}
      user: {current_user_email}
      app: {app_info_dict}
      context: {repr(anvil.server.context)}
      app_origin: {anvil.server.get_app_origin()}
      """
    )
    print(f"Reporting error: {content}")
    n.email_send(admin, subject="empathy.chat error", text=content, from_name="empathy.chat error handling")


@anvil.server.callable
def warning(warning_str, app_info_dict=None):
  from . import notifies as n
  admin = app_tables.users.get(email="hugetim@gmail.com")
  current_user = anvil.users.get_user()
  if admin != current_user:
    current_user_email = current_user['email'] if current_user else ""
    content = (
      f"""{warning_str}
      user: {current_user_email}
      app: {app_info_dict}
      context: {repr(anvil.server.context)}
      app_origin: {anvil.server.get_app_origin()}
      """
    )
    print(f"Reporting warning: {warning_str}")
    n.email_send(admin, subject="empathy.chat warning", text=content, from_name="empathy.chat error handling")
    
    
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
    user = app_tables.users.add_row(email=email, enabled=True, signed_up=now())
    return user, True
  else:
    return user, False

  
# @anvil.server.callable
# @anvil.tables.in_transaction
# def do_google_signup(email):
#   if anvil.google.auth.get_user_email() == email:
#     user = app_tables.users.get(email=email)
#     if not user:
#       user = app_tables.users.add_row(email=email, enabled=True, signed_up=now())
#       anvil.users.force_login(user)
#     return user


@anvil.tables.in_transaction(relaxed=True)
def _init_user_info_transaction(user, time_zone):
  return init_user_info(user, time_zone)


def init_user_info(user, time_zone=""):
  """Return trust, initializing info for new users & updating trust_level"""
  user['time_zone'] = time_zone
  user['init_date'] = now()
  if user['trust_level'] is None:
    user['notif_settings'] = {"essential": "sms",
                              "message": "email",
                              "email": {"eligible":1, "eligible_users":[], "eligible_groups":[], "eligible_starred":true},
                              "sms": {"eligible":0, "eligible_users":[], "eligible_groups":[], "eligible_starred":false},
                             }
    user['first_name'] = ""
    user['last_name'] = ""
    user['how_empathy'] = ""
    user['profile'] = ""
    user['phone'] = ""
    user['confirmed_url'] = ""


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
  if (trust >= 3 and trust < 4) and user['confirmed_url']:
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


def as_user_tz(dt, user):
  import pytz
  tz_user = pytz.timezone(user['time_zone'])
  return dt.astimezone(tz_user)


def name(user, to_user=None, distance=None):
  if distance is None:
    if to_user:
      from . import connections as c
      distance = c.distance(user, to_user, up_to_distance=2)
    else:
      distance = port.UNLINKED
  return port.full_name(user['first_name'], user['last_name'], distance)  


@authenticated_callable
def get_port_user(user2, distance=None, user1_id="", simple=False):
  if user2:
    user1 = get_acting_user(user1_id)
    if user1 == user2:
      distance = 0
    _name = name(user2, user1 if user1_id else None, distance)
    if simple:
      return port.User(user2.get_id(), _name)
    else:
      return port.User(user_id=user2.get_id(), 
                       name=_name,
                       confirmed_url=user2['confirmed_url'],
                       distance=distance,
                       seeking=user2['seeking_buddy'],
                       starred=bool(star_row(user2, user1)) if user2 != user1 else None, #True/False
                      )
  else:
    return None

  
@authenticated_callable
def get_port_user_full(user2, user1_id="", distance=None, degree=None, common_group_names=None):
  from . import connections as c
  user1 = get_acting_user(user1_id)
  return port.UserFull(**c.connection_record(user2=user2, user1=user1, _distance=distance, degree=degree), 
                       common_group_names=common_group_names)


def get_port_users_full(user2s, user1_id="", up_to_distance=3):
  from . import connections as c
  user1 = get_acting_user(user1_id)
  distances = c.distances(user2s, user1, up_to_distance)
  return [get_port_user_full(user2, user1_id, distance=distances[user2], degree=distances[user2]) for user2 in user2s]
 
  
@authenticated_callable
def init_create_form(user_id=""):
  from . import connections as c
  from . import groups_server as g
  user = get_acting_user(user_id)
  create_user_items, starred_name_list = c.get_create_user_items(user)
  create_group_items = g.get_create_group_items(user)
  return create_user_items, create_group_items, starred_name_list
  
  
def _latest_invited(user):
  inviteds = _inviteds(user)
  if len(inviteds) == 0:
    return None
  else:
    return inviteds[0]

  
def _inviteds(user):
  return app_tables.invites.search(order_by("date", ascending=False), origin=True, user2=user, current=True)


@anvil.tables.in_transaction(relaxed=True)
@timed
def get_prompts(user):
  import datetime
  out = []
  other_prompts = app_tables.prompts.search(user=user)
  if len(other_prompts) > 0:
    for prompt in other_prompts:
      if prompt['dismissed']: continue
      spec = prompt['spec']
      spec['prompt_id'] = prompt.get_id() 
      out.append(spec)
  invited = _latest_invited(user)
  if not user['phone']:
    if invited:
      out.append({"name": "phone-invited", "inviter": name(invited['user1'], to_user=user)})
    else:
      out.append({"name": "phone"})
  else:
    if invited:
      for invite in _inviteds(user):
        out.append({"name": "invited", "inviter": name(invite['user1'], to_user=user), 
                    "inviter_id": invite['user1'].get_id(), "rel": invite['relationship2to1']})
    if user['trust_level'] == 2:
      import connections as c
      members = c.member_close_connections(user)
      if members:
        out.append({"name": "member-chat", "members": [get_port_user(m, distance=1, simple=True) for m in members]})
#       else:
#         out.append({"name": "invite-close"})
    elif (not invited and not [s for s in out if s['name'] == "connected"]
          and (not user['last_invite'] or user['last_invite'] < now() - datetime.timedelta(days=90))):
      out.append({"name": "invite-close"})
  return out


@authenticated_callable
@anvil.tables.in_transaction(relaxed=True)
def dismiss_prompt(prompt_id):
  from . import matcher
  matcher.propagate_update_needed()
  prompt = app_tables.prompts.get_by_id(prompt_id)
  prompt['dismissed'] = True
  

@authenticated_callable
def invited_item(inviter_id, user_id=""):
  user = get_acting_user(user_id)
  inviter_user = get_other_user(inviter_id)
  inviteds = app_tables.invites.search(order_by("date", ascending=False), origin=True, user1=inviter_user, user2=user, current=True)
  return {"inviter": name(inviter_user, to_user=user), "link_key": inviteds[0]['link_key'],
          "inviter_id": inviter_id, "rel": inviteds[0]['relationship2to1']}


@authenticated_callable
def init_profile(user_id=""):
  from . import connections as c
  user = get_other_user(user_id)
  record = c.connection_record(user, get_acting_user())
  record.update({'relationships': [] if record['me'] else c.get_relationships(user),
                 'how_empathy': user['how_empathy'],
                 'profile': user['profile'],
                })
  return port.UserProfile(**record)
    
  
@authenticated_callable
def set_seeking_buddy(seeking, user_id=""):
  user = get_acting_user(user_id)
  from . import matcher
  matcher.propagate_update_needed(user)
  user['seeking_buddy'] = seeking
  
  
@authenticated_callable
def save_name(name_item, user_id=""):
  user = get_acting_user(user_id)
  from . import matcher
  matcher.propagate_update_needed(user)
  user['first_name'] = name_item['first']
  user['last_name'] = name_item['last']
  
  
@authenticated_callable
def save_user_field(item_name, value, user_id=""):
  user = get_acting_user(user_id)
  user[item_name] = value
  
  
@authenticated_callable
def save_starred(new_starred, user2_id, user_id=""):
  user = get_acting_user(user_id)
  from . import matcher
  matcher.propagate_update_needed()
  user2 = get_other_user(user2_id)
  _star_row = star_row(user2, user)
  if new_starred and not _star_row:
    app_tables.stars.add_row(user1=user, user2=user2)
  elif not new_starred and _star_row:
    _star_row.delete()
  else:
    warning("Redundant save_starred call.")

    
def star_row(user2, user1):
  return app_tables.stars.get(user1=user1, user2=user2)


def starred_users(user):
  for row in app_tables.stars.search(user1=user):
    yield row['user2']
  

class ServerItem:
  def relay(self, method, kwargs=None):
    if not kwargs:
      kwargs = {}
    return getattr(self, method)(**kwargs)
  

def new_jitsi_code():
  if DEBUG:
    print("server_misc.new_jitsi_code()")
  return "empathy-chat-" + random_code()


def random_code(num_chars=5, digits_only=False):
  import random
  if digits_only:
    charset = "1234567890"
  else:
    charset = "abcdefghijkmnopqrstuvwxyz23456789"
  random.seed()
  return "".join([random.choice(charset) for i in range(num_chars)])


def prune_chat_messages():
  """Prune messages from fully completed matches"""
  if DEBUG:
    print("server_misc.prune_chat_messages()")
  all_messages = app_tables.chat.search()
  matches = {message['match'] for message in all_messages}
  for match in matches:
    if min(match['complete']) == 1:
      for row in app_tables.chat.search(match=match):
        row.delete()

        
@authenticated_callable
def update_history_form(user2_id, user_id=""):
  """
  Return (iterable of dictionaries with keys: 'me', 'message'), their_value
  """
  user = get_acting_user(user_id)
  user2 = get_other_user(user2_id)
  return _update_history_form(user2, user)


def _update_history_form(user2, user1):
  messages = app_tables.messages.search(
    anvil.tables.order_by("time_stamp", ascending=True),
    q.any_of(q.all_of(from_user=user2, to_user=user1),
             q.all_of(from_user=user1, to_user=user2),
            )
  )
  if messages:
    return [{'me': (user1 == m['from_user']),
             'message': anvil.secrets.decrypt_with_key("new_key", m['message']),
             'time_stamp': m['time_stamp'],
            } for m in messages]
  else:
    return []

  
@authenticated_callable
def add_message(user2_id, user_id="", message="[blank test message]"):
  print(f"add_message, '[redacted]', {user_id}")
  user = get_acting_user(user_id)
  user2 = get_other_user(user2_id)
  app_tables.messages.add_row(from_user=user,
                              to_user=user2,
                              message=anvil.secrets.encrypt_with_key("new_key", message),
                              time_stamp=now())
  _add_message_prompt(user2, user)
  from . import matcher
  matcher.propagate_update_needed(user)
  return _update_history_form(user2, user)

  
def _add_message_prompt(user2, user1):
  such_prompts = app_tables.prompts.search(user=user2, dismissed=False, spec={"name": "message", "from_id": user1.get_id()})
  if len(such_prompts) == 0:
    from_name = name(user1, to_user=user2)
    app_tables.prompts.add_row(user=user2, date=now(), dismissed=False,
                             spec={"name": "message", "from_name": from_name, "from_id": user1.get_id()}
                            )
    from . import notifies as n
    n.notify_message(user2, from_name)
    

def _connected_prompt(invite, invite_reply):
  return dict(user=invite['user1'],
              spec={"name": "connected", "to_name": name(invite['user2'], distance=invite['distance']), 
                    "to_id": invite['user2'].get_id(), "rel": invite_reply['relationship2to1'],},
              date=now(),
              dismissed=False,
             )


def add_invite_guess_fail_prompt(s_invite):
  prompt_dict = _invite_guess_fail_prompt(s_invite)
  if not app_tables.prompts.get(user=prompt_dict['user'], spec={"name": "invite_guess_fail", 
                                                                "guess": prompt_dict['spec']['guess'],
                                                                "to_id": prompt_dict['spec']['to_id']}):
    app_tables.prompts.add_row(**prompt_dict)


def _invite_guess_fail_prompt(s_invite):
  return dict(user=s_invite.inviter,
              spec={"name": "invite_guess_fail", "rel": s_invite.rel_to_inviter, "guess": s_invite.inviter_guess,
                    "to_name": name(s_invite.invitee), "to_id": s_invite.invitee.get_id(), },
              date=now(),
              dismissed=False,
             )


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


@authenticated_callable
def get_settings(user_id=""):
  """Return user settings displayed on SettingsForm"""
  from . import groups
  user = get_acting_user(user_id)
  item_lists = {}
  item_lists['user_items'], item_lists['group_items'], item_lists['starred_name_list'] = init_create_form(user_id)
  notif_settings = dict(user['notif_settings'])
  elig_items = {}
  for medium in ['sms', 'email']:
    elig_items[medium] = notif_settings.pop(medium) if notif_settings.get(medium) else dict(eligible=0, eligible_starred=False, eligible_users=[], eligible_groups=[])
    elig_items[medium]['eligible_users'] = [get_port_user(get_other_user(u_id), simple=True) for u_id in elig_items[medium]['eligible_users']]
    eligible_group_rows = [app_tables.groups.get_by_id(g_id) for g_id in elig_items[medium]['eligible_groups']]
    elig_items[medium]['eligible_groups'] = [groups.Group(group_row['name'], group_row.get_id()) for group_row in eligible_group_rows]
    elig_items[medium].update(item_lists)
  return (user['phone'], notif_settings, elig_items)


@authenticated_callable
@anvil.tables.in_transaction(relaxed=True)
def set_notif_settings(notif_settings, elig_items, user_id=""):
  print(f"set_notif_settings, {notif_settings}")
  from . import groups
  user = get_acting_user(user_id)
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
      specs[medium]['eligible_users'] = [get_other_user(u_id) for u_id in notif_settings[medium]['eligible_users']]
      specs[medium]['eligible_groups'] = [app_tables.groups.get_by_id(g_id) for g_id in notif_settings[medium]['eligible_groups']]
  return specs


def _number_already_taken(number):
  return bool(len(app_tables.users.search(phone=number)))


@authenticated_callable
def send_verification_sms(number, user_id=""):
  if _number_already_taken(number):
    return "number unavailable"
  else:
    user = get_acting_user()
    code = random_code(num_chars=6, digits_only=True)
    from . import notifies as n
    error_message = n.send_sms(
      number, 
      f"{code} is your empathy.chat verification code. It expires in 10 minutes."
    )
    if error_message:
      return error_message
    else:
      app_tables.codes.add_row(
        type="phone",
        address=number,
        code=code,
        user=user,
        date=now()
      )
      return "code sent"
  
  
@authenticated_callable
@anvil.tables.in_transaction
def check_phone_code(code, user_id=""):
  import datetime
  user = get_acting_user(user_id)
  from . import matcher
  matcher.propagate_update_needed()
  # first expunge old codes
  _now = now()
  for code_row in app_tables.codes.search():
    if _now - code_row['date'] > datetime.timedelta(minutes=10):
      code_row.delete()
  current_code_rows = app_tables.codes.search(order_by("date", ascending=False), user=user, type="phone")
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
  for invite_row in _inviteds(user):
    invite_reply = app_tables.invites.get(origin=False, user1=user, link_key=invite_row['link_key'], current=True)
    if invite_reply:
      from . import connections as c
      if c.try_connect(invite_row, invite_reply):
        any_confirmed = True
      else:
        any_failed = True
        from . import invites_server
        add_invite_guess_fail_prompt(invites_server.Invite.from_invite_row(invite_row))
        c.remove_invite_pair(invite_row, invite_reply, user)
    else:
      warning(f"invite_reply not found, {dict(invite_row)}")
  return any_confirmed, any_failed


@anvil.server.http_endpoint('/:name')
def get_doc(name):
  return app_tables.files.get(name=name)['file']


@anvil.server.callable
def get_url(name):
  url = anvil.server.get_api_origin() +'/'+name
  return url


@anvil.server.callable
def get_urls(names):
  return [get_url(name) for name in names]
