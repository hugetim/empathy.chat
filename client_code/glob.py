import anvil.users
import anvil.server
from . import parameters as p
from . import groups
from anvil_extras.messaging import Publisher


MOBILE = None
trust_level = 0
name = ""
invites = []
my_groups = groups.MyGroups()
logged_in_user = None
logged_in_user_id = ""
publisher = Publisher(with_logging=False)


# A private variable to cache the values once we've fetched them
_lazy_dict = {}
lazy_loaded = False


def __getattr__(name):
  if name in ['user_items', 'group_items', 'starred_name_list']: 
    global _lazy_dict
    # fetch the value if we haven't loaded it already:
    trial_get = _lazy_dict.get(name)
    if trial_get:
      return trial_get
    else:
      populate_lazy_vars()          
      return _lazy_dict.get(name)
  raise AttributeError(name)
 

def populate_lazy_vars(spinner=True):
  if spinner:
    out = anvil.server.call('init_create_form')
  else:
    out = anvil.server.call_s('init_create_form')
  _set_lazy_vars(out)

    
def _set_lazy_vars(out):
  global _lazy_dict
  global lazy_loaded
  _user_items, _group_items, _starred_name_list = out
  _lazy_dict = {'user_items': _user_items, 'group_items': _group_items,
                'starred_name_list': _starred_name_list,
               }
  lazy_loaded = True
