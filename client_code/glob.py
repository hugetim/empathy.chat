import anvil.server
from . import parameters as p
from . import groups
from anvil_extras.messaging import Publisher


MOBILE = None
trust_level = 0
name = ""
invites = []
logged_in_user = None
logged_in_user_id = ""
publisher = Publisher(with_logging=False)


# A private variable to cache the values once we've fetched them
_lazy_dict = {}
lazy_loaded = False


def __getattr__(name):
  if name in ['users', 'connections', 'my_groups', 'their_groups', 'user_items', 'group_items', 'starred_name_list']: 
    from .ui_procedures import loading_indicator
    global _lazy_dict
    # fetch the value if we haven't loaded it already:
    with loading_indicator:
      while True:
        trial_get = _lazy_dict.get(name)
        if trial_get != None:
          return trial_get
        import time
        time.sleep(2)
          # populate_lazy_vars()          
          # return _lazy_dict.get(name)
  raise AttributeError(name)
 

def populate_lazy_vars(spinner=True):
  if spinner:
    out = anvil.server.call('init_cache')
  else:
    out = anvil.server.call_s('init_cache')
  _set_lazy_vars(out)


def update_lazy_vars(spinner=True):
  _clear_lazy_vars()
  populate_lazy_vars(spinner)


def _clear_lazy_vars():
  global _lazy_dict
  _lazy_dict = {}
  lazy_loaded = False

  
def _set_lazy_vars(out):
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


def port_logged_in_user():
  if logged_in_user_id:
    return users[logged_in_user_id]
  else:
    return None  
