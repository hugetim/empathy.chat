import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from . import server_misc as sm
from .server_misc import authenticated_callable
from . import matcher
from . import portable as port


def is_visible(user2, user1=None): # Currently unused
  """Is user2 visible to user1?"""
  if matcher.DEBUG:
    print("server_misc.is_visible")
  if user1 is None:
    user1 = anvil.server.session['user']
  trust1 = user1['trust_level']
  trust2 = user2['trust_level']
  if trust1 is None:
    return False
  elif trust2 is None:
    return False
  else:
    return trust1 > 0 and trust2 > 0 and _distance(user2, user1) <= 3

  
@authenticated_callable
def get_create_user_items(user_id=""):
  """Return list with 1st---2nd""" # add pending connections to front
  print("get_create_user_items", user_id)
  user = sm.get_user(user_id)
  dset = _get_connections(user, 2)
  items = {}
  for degree in [1, 2]:
    items[degree] = [port.User.get(other, distance=degree).item() for other in dset[degree]]
  return items[1] + ["---"] + items[2]


