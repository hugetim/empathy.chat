import anvil.server
from anvil_extras.messaging import Publisher


MOBILE = None
APPLE = None
trust_level = 0
name = ""
invites = []
logged_in_user = None
logged_in_user_id = ""
default_request = None
publisher = Publisher(with_logging=False)

# A private variable to cache the values once we've fetched them
_lazy_dict = {}
lazy_loaded = False
cache_task = None
CACHE_KEYS = {'users', 'connections', 'my_groups', 'their_groups', 'user_items', 'group_items', 'starred_name_list'}


def logout():
  global trust_level, name, invites, logged_in_user, logged_in_user_id, default_request
  trust_level = 0
  name = ""
  invites = []
  logged_in_user = None
  logged_in_user_id = ""
  default_request = None
  clear_lazy_vars()
  

def __getattr__(name):
  if name in CACHE_KEYS: 
    return _get_cached(name)
  else:
    raise AttributeError(name)


def _get_cached(name):
  from .ui_procedures import loading_indicator
  trial_get = _trial_get(name)
  with loading_indicator:
    while trial_get is None:
      import time
      time.sleep(.1)
      trial_get = _trial_get(name)
    else:
      return trial_get


def _trial_get(name):
  trial_get = _lazy_dict.get(name)
  if trial_get is None and cache_task and cache_task.is_completed():
    set_lazy_vars(cache_task.get_state()['out'])
    trial_get = _lazy_dict.get(name)
  return trial_get

  
def set_lazy_vars(out):
  from . import network_controller as nc
  global _lazy_dict
  global lazy_loaded
  _users, _connections, _my_groups, _their_groups = out
  _lazy_dict = {
    'users': _users, 'connections': _connections, 'my_groups': _my_groups, 'their_groups': _their_groups, 
  }
  _group_items = nc.get_create_group_items()
  _user_items, _starred_name_list = nc.get_create_user_items()
  _lazy_dict.update({
    'user_items': _user_items, 'group_items': _group_items, 'starred_name_list': _starred_name_list,
  })
  lazy_loaded = True


def reset_get_create_user_items():
  from . import network_controller as nc
  global _lazy_dict
  _user_items, _starred_name_list = nc.get_create_user_items()
  _lazy_dict.update({
    'user_items': _user_items, 'starred_name_list': _starred_name_list,
  })

  
def populate_lazy_vars(spinner=True):
  if spinner:
    out = anvil.server.call('init_cache')
  else:
    out = anvil.server.call_s('init_cache')
  set_lazy_vars(out)


def update_lazy_vars(spinner=True):
  clear_lazy_vars()
  populate_lazy_vars(spinner)


def clear_lazy_vars():
  global _lazy_dict
  global lazy_loaded
  global cache_task
  _lazy_dict = {}
  lazy_loaded = False
  cache_task = None
