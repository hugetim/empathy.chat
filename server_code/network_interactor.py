from anvil import secrets
from .server_misc import authenticated_callable
from anvil.server import background_task, launch_background_task
from anvil_extras.server_utils import timed
from . import server_misc as sm
from .network_gateway import NetworkRepository


repo = NetworkRepository()


@authenticated_callable
@timed
def init_cache(user=None):
  from . import connections as c
  if not user:
    user = sm.get_acting_user()
  users_dict, connections_list, their_groups_dict = c.init_connections(user=user)
  port_my_groups = _init_my_groups(user)
  return users_dict, connections_list, port_my_groups, their_groups_dict


def _init_my_groups(user):
  from . import groups_server as g
  return g.load_my_groups(user=user)


@authenticated_callable
def add_message(user2_id, user_id="", message="[blank test message]"):
  print(f"add_message, '[redacted]', {user_id}")
  user = sm.get_acting_user(user_id)
  user2 = sm.get_other_user(user2_id)
  repo.add_message(from_user=user,
                   to_user=user2,
                   message=secrets.encrypt_with_key("new_key", message),
                   time_stamp=sm.now())
  launch_background_task('add_message_prompt', user2, user)
  return get_messages(user2, user)


@authenticated_callable
def update_history_form(user2_id, user_id=""):
  """
  Return (iterable of dictionaries with keys: 'me', 'message'), their_value
  """
  user = sm.get_acting_user(user_id)
  user2 = sm.get_other_user(user2_id)
  return get_messages(user2, user)
  

def get_messages(user2, user1):
  messages = repo.get_messages(user2, user1)
  if messages:
    return [{'me': (user1 == m['from_user']),
             'message': secrets.decrypt_with_key("new_key", m['message']),
             'time_stamp': m['time_stamp'],
            } for m in messages]
  else:
    return []


@background_task
def prune_chat_messages():
  """Prune messages from fully completed matches"""
  from anvil.tables import app_tables
  if sm.DEBUG:
    print("prune_chat_messages()")
  all_messages = app_tables.chat.search()
  matches = {message['match'] for message in all_messages}
  for match in matches:
    if min(match['complete']) == 1:
      for row in app_tables.chat.search(match=match):
        row.delete()

    
@authenticated_callable
def save_starred(new_starred, user2_id, user_id=""):
  from anvil.tables import app_tables
  from . import matcher
  user = sm.get_acting_user(user_id)
  user2 = sm.get_other_user(user2_id)
  _star_row = star_row(user2, user)
  if new_starred and not _star_row:
    app_tables.stars.add_row(user1=user, user2=user2)
  elif not new_starred and _star_row:
    _star_row.delete()
  else:
    sm.warning("Redundant save_starred call.")
  matcher.propagate_update_needed()

    
def star_row(user2, user1):
  from anvil.tables import app_tables
  return app_tables.stars.get(user1=user1, user2=user2)


def starred_users(user):
  from anvil.tables import app_tables
  for row in app_tables.stars.search(q.fetch_only(user2=q.fetch_only('first_name')), user1=user):
    yield row['user2']
  