import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from . import server_misc as sm
from .server_misc import authenticated_callable
from . import portable as port
from . import parameters as p


def is_visible(user2, user1=None): # Currently unused
  """Is user2 visible to user1?"""
  if sm.DEBUG:
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
    return trust1 > 0 and trust2 > 0 and distance(user2, user1) <= 3

  
@authenticated_callable
def get_create_user_items(user_id=""):
  """Return list with 1st---2nd""" # add pending connections to front
  print("get_create_user_items", user_id)
  user = sm.get_user(user_id)
  dset = _get_connections(user, 2)
  items = {}
  for degree in [1, 2]:
    items[degree] = [sm.get_port_user(other, distance=degree).item() for other in dset[degree]]
  return items[1] + ["---"] + items[2]


def _get_connections(user, up_to_degree=3, include_zero=False):
  """Return dictionary from degree to set of connections"""
  assert (up_to_degree in range(1, 99)) or (include_zero and up_to_degree == 0)
  degree1s = set([row['user2'] for row in app_tables.connections.search(user1=user)])
  out = {0: {user}, 1: degree1s}
  assert user not in out[1]
  prev = set()
  for d in range(up_to_degree):
    current = set()
    prev.update(out[d])
    current.update(
      {row['user2'] for row in app_tables.connections.search(user1=q.any_of(*out[d]))
        if row['user2'] not in prev
      }
    )
    out[d+1] = current
  if not include_zero:
    del out[0]
  return out
    
    
def _degree(user2, user1, up_to_degree=3):
  """Returns 99 if no degree <= up_to_degree found"""
  dset = _get_connections(user1, up_to_degree)
  if user2 == user1:
    return 0
  else:
    for d in range(1, up_to_degree+1):
      if user2 in dset[d]:
        return d
    return 99


def distance(user2, user1, up_to_distance=3):
  return _degree(user2, user1, up_to_distance)

@authenticated_callable
def get_connections(user_id):
  print("get_connections", user_id)
  user = sm.get_user(user_id, require_auth=False)
  is_me = user == anvil.server.session['user']
  up_to_degree = 3
  dset = _get_connections(anvil.server.session['user'], up_to_degree, include_zero=True)
  if is_me:
    user2s = []
    for d in range(1, up_to_degree+1):
      user2s += dset[d]
    return [connection_record(user2, user) for user2 in user2s]
  elif (anvil.server.session['trust_level'] < sm.TEST_TRUST_LEVEL
        and _degree(user, anvil.server.session['user']) > 1):
    return []
  else:
    dset2 = _get_connections(user, 1)
    user2s = []
    for d in range(0, up_to_degree+1):
      user2s += dset[d] & dset2[1]
    return [connection_record(user2, anvil.server.session['user']) for user2 in user2s]


def connection_record(user2, user1):
  degree = _degree(user2, user1)
  _distance = distance(user2, user1)
  record = vars(sm.get_port_user(user2, _distance))
  record.update({'degree': degree, 
                 'last_active': user2['last_login'].strftime(p.DATE_FORMAT),
                 'status': "", # invited, invite
                 'unread_message': None, # True/False
                })
  return record


def get_relationships(user2, user1_id="", up_to_degree=3):
  """Returns ordered list of dictionaries"""
  user1 = sm.get_user(user1_id)
  dset = _get_connections(user1, up_to_degree)
  if user2 == user1:
    return []
  else:
    degree = None
    for d in range(1, up_to_degree+1):
      if user2 in dset[d]:
        degree = d
        break
    if not degree: 
      return []
    elif degree == 1:
      conn = app_tables.connections.get(user1=user1, user2=user2)
      return [{"via": False, 
               "whose": "my", 
               "desc": conn['relationship2to1'], 
               "date": conn['date_described'].strftime(p.DATE_FORMAT), 
               "child": None}]
    #[{"via": True, "whose": "", "desc": "", "date": ""}] if degree <= 2 else 
    out = []
    dset2 = _get_connections(user2, degree-2, include_zero=True)
    seconds = dset[2] & dset2[degree-2]
    for second in seconds:
      dset_second = _get_connections(second, 1)
      firsts = dset[1] & dset_second[1]
      for first in firsts:
        name = port.full_name(first['first_name'], first['last_name'], 1)
        conn2 = app_tables.connections.get(user1=first, user2=second)
        conn1 = app_tables.connections.get(user1=user1, user2=first)
        out.append({"via": degree > 2,
                    "whose": f"{name}'s", 
                    "desc": conn2['relationship2to1'],
                    "date": conn2['date_described'].strftime(p.DATE_FORMAT),
                    "child": {"via": False,
                              "whose": "my", 
                              "desc": conn1['relationship2to1'],
                              "date": conn1['date_described'].strftime(p.DATE_FORMAT),
                              "child": None,
                             },
                   })
    return out 

  
@authenticated_callable
def cancel_invite(link_key, user_id=""):
  user = sm.get_user(user_id)
  row = app_tables.invites.get(link_key=link_key)
  if row:
    row.delete()


@authenticated_callable
@anvil.tables.in_transaction
def add_invite(item, user_id=""):
  user = sm.get_user(user_id)
  now = sm.now()
  link_key = sm.random_code(num_chars=7)
  app_tables.invites.add_row(date=now,
                             user1=user,
                             relationship2to1=item['relationship'],
                             date_described=now,
                             guess=item['phone_last4'],
                             distance=1,
                             link_key=link_key,
                            )
  return {"link_key": link_key,
          "invite_url": f"{p.URL}#?invite={link_key}"}

@anvil.server.callable
def invite_visit(link_key):
  invite = app_tables.invites.get(link_key=link_key)
  if invite:
    anvil.server.session['invite_link_key'] = link_key
    return True
  else:
    return False