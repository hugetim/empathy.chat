from anvil import secrets
from .server_misc import authenticated_callable
from anvil_extras.server_utils import timed
from . import server_misc as sm
from .network_gateway import NetworkRepository


repo = NetworkRepository()


@authenticated_callable
@timed
def init_cache():
  from . import connections as c
  users_dict, connections_list, their_groups_dict = c.init_connections()
  port_my_groups = _init_my_groups()
  return users_dict, connections_list, port_my_groups, their_groups_dict


def _init_my_groups():
  from . import groups_server as g
  return g.load_my_groups()


@authenticated_callable
def add_message(user2_id, user_id="", message="[blank test message]"):
  print(f"add_message, '[redacted]', {user_id}")
  user = sm.get_acting_user(user_id)
  user2 = sm.get_other_user(user2_id)
  repo.add_message(from_user=user,
                   to_user=user2,
                   message=secrets.encrypt_with_key("new_key", message),
                   time_stamp=sm.now())
  sm.add_message_prompt(user2, user)
  from . import matcher
  matcher.propagate_update_needed(user)
  return _get_messages(user2, user)


@authenticated_callable
def update_history_form(user2_id, user_id=""):
  """
  Return (iterable of dictionaries with keys: 'me', 'message'), their_value
  """
  user = sm.get_acting_user(user_id)
  user2 = sm.get_other_user(user2_id)
  return _get_messages(user2, user)
  

def _get_messages(user2, user1):
  messages = repo.get_messages(user2, user1)
  if messages:
    return [{'me': (user1 == m['from_user']),
             'message': secrets.decrypt_with_key("new_key", m['message']),
             'time_stamp': m['time_stamp'],
            } for m in messages]
  else:
    return []