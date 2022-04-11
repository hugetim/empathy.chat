import anvil.users
import anvil.server
import anvil.tables
from anvil.tables import app_tables, order_by
import anvil.tables.query as q
from anvil import secrets
from . import parameters as p
from . import portable as port
from anvil_extras.server_utils import timed


DEBUG = False #p.DEBUG_MODE
TEST_TRUST_LEVEL = 10
authenticated_callable = anvil.server.callable(require_user=True)


def now():
  """Return utcnow"""
  import datetime
  return datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc())

    
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
  admin = app_tables.users.get(email=secrets.get_secret('admin_email'))
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
def warning(warning_str, app_info_dict=None, from_client=False):
  from . import notifies as n
  admin = app_tables.users.get(email=secrets.get_secret('admin_email'))
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
    if not from_client:
      print(f"Reporting warning: {warning_str}")
    n.email_send(admin, subject="empathy.chat warning", text=content, from_name="empathy.chat warning handling")
    
    
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
                       confirmed_url=user2['confirmed_url'] if user2['confirmed_url_date'] else None,
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
  _inviteds = inviteds(user)
  if len(_inviteds) == 0:
    return None
  else:
    return _inviteds[0]

  
def inviteds(user):
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
      for invite in inviteds(user):
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
  _inviteds = app_tables.invites.search(order_by("date", ascending=False), origin=True, user1=inviter_user, user2=user, current=True)
  return {"inviter": name(inviter_user, to_user=user), "link_key": _inviteds[0]['link_key'],
          "inviter_id": inviter_id, "rel": _inviteds[0]['relationship2to1']}


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


def _add_message_prompt(user2, user1):
  such_prompts = app_tables.prompts.search(user=user2, dismissed=False, spec={"name": "message", "from_id": user1.get_id()})
  if len(such_prompts) == 0:
    from_name = name(user1, to_user=user2)
    app_tables.prompts.add_row(user=user2, date=now(), dismissed=False,
                             spec={"name": "message", "from_name": from_name, "from_id": user1.get_id()}
                            )
    from . import notifies as n
    n.notify_message(user2, from_name)


@authenticated_callable
def add_message(user2_id, user_id="", message="[blank test message]"):
  print(f"add_message, '[redacted]', {user_id}")
  user = get_acting_user(user_id)
  user2 = get_other_user(user2_id)
  app_tables.messages.add_row(from_user=user,
                              to_user=user2,
                              message=secrets.encrypt_with_key("new_key", message),
                              time_stamp=now())
  _add_message_prompt(user2, user)
  from . import matcher
  matcher.propagate_update_needed(user)
  return _update_history_form(user2, user)


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
             'message': secrets.decrypt_with_key("new_key", m['message']),
             'time_stamp': m['time_stamp'],
            } for m in messages]
  else:
    return []
    
    
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
