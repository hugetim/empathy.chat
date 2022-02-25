import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from . import server_misc as sm
from .server_misc import authenticated_callable
from . import portable as port
from . import parameters as p
from . import helper as h
from anvil_extras.server_utils import timed


# def is_visible(user2, user1=None): # Currently unused
#   """Is user2 visible to user1?"""
#   if sm.DEBUG:
#     print("c.is_visible")
#   if user1 is None:
#     user1 = anvil.users.get_user()
#   trust1 = user1['trust_level']
#   trust2 = user2['trust_level']
#   if trust1 is None:
#     return False
#   elif trust2 is None:
#     return False
#   else:
#     return trust1 > 0 and trust2 > 0 and distance(user2, user1) <= 3

  
def get_create_user_items(user):
  """Return list with 1st---2nd""" # add pending connections to front
  if sm.DEBUG:
    print(f"get_create_user_items, {user['email']}")
  dset = _get_connections(user, 2)
  dset[2] = [other for other in dset[2] if other['trust_level'] >= 3]
  items = {}
  degree_set = [1, 2] if user['trust_level'] >= 3 else [1]
  for degree in degree_set:
    # change to distance=distance(user2, user1) or equivalent once properly implement distance
    items[degree] = [sm.get_port_user(other, distance=degree).name_item() for other in dset[degree]]
    items[degree].sort(key=lambda user_item: user_item[0])
  starred_name_list = [sm.name(u, distance=_degree_from_dset(u, dset)) for u in sm.starred_users(user)]
  if user['trust_level'] >= 3 and items[2]:
    return items[1] + ["---"] + items[2], starred_name_list
  else:
    return items[1], starred_name_list


def _get_connections(user, up_to_degree=3, cache_override=False):
  """Return dictionary from degree to set of connections"""
  if up_to_degree not in range(0, 98):
    sm.warning(f"_get_connections(user, {up_to_degree}) not expected")
  if not cache_override and user == anvil.users.get_user():
    return _cached_get_connections(user, up_to_degree)
  degree1s = {row['user2'] for row in app_tables.connections.search(user1=user, current=True)}
  out = {0: {user}, 1: degree1s}
  if user in out[1]:
    sm.warning(f"user in out[1]")
  prev = {user}
  for d in range(1, up_to_degree):
    prev.update(out[d])
    current = {row['user2'] for row in app_tables.connections.search(user1=q.any_of(*out[d]), current=True)}
    out[d+1] = current - prev
  return out


_cached_connections = {}
_cached_up_to = -1

def _cached_get_connections(logged_in_user, up_to_degree):
  global _cached_connections
  global _cached_up_to
  if up_to_degree > _cached_up_to:
    _cached_connections = _get_connections(logged_in_user, up_to_degree=up_to_degree, cache_override=True)
    _cached_up_to = up_to_degree
  return {key: _cached_connections[key].copy() for key in range(up_to_degree+1)}


def _clear_cached_connections():
  global _cached_connections
  global _cached_up_to
  _cached_connections = {}
  _cached_up_to = -1

  
def member_close_connections(user):
  """Returns list of users"""
  degree1s = _get_connections(user, 1)[1]
  return [user2 for user2 in degree1s
          if user2['trust_level'] >= 3 and distance(user2, user, up_to_distance=1) == 1]
  

def _degree(user2, user1, up_to_degree=3):
  """Returns port.UNLINKED if no degree <= up_to_degree found"""
  if user2 == user1:
    return 0
  else:
    dset = _get_connections(user1, up_to_degree)
    del dset[0]
    return _degree_from_dset(user2, dset)

  
def _degree_from_dset(user2, dset):
  for d in dset:
    if user2 in dset[d]:
      return d
  return port.UNLINKED
  

def _degrees(user2s, user1, up_to_degree=3):
  """Returns port.UNLINKED if no degree <= up_to_degree found"""
  dset = _get_connections(user1, up_to_degree)
  out = {}
  for user2 in set(user2s):
    out[user2] = _degree_from_dset(user2, dset)
  return out
  

def distance(user2, user1, up_to_distance=3):
  return _degree(user2, user1, up_to_distance)


def distances(user2s, user1, up_to_distance=3):
  return _degrees(user2s, user1, up_to_distance)


@authenticated_callable
def get_connections(user_id):
  print(f"get_connections, {user_id}")
  user = sm.get_user(user_id, require_auth=False)
  logged_in_user = anvil.users.get_user()
  is_me = user == logged_in_user
  up_to_degree = 3
  dset = _get_connections(logged_in_user, up_to_degree)
  if is_me:
    records = []
    c_users = set()
    for d in range(1, up_to_degree+1):
      records += [sm.get_port_user_full(user2, distance=d, degree=d) for user2 in dset[d]]
      c_users.update(dset[d])
    return records + _group_member_records_exclude(logged_in_user, c_users)
  elif (logged_in_user['trust_level'] < sm.TEST_TRUST_LEVEL
        and _degree_from_dset(user, dset) > 1):
    return []
  else:
    dset2 = _get_connections(user, 1)
    records = []
    for d in range(0, up_to_degree+1):
      records += [sm.get_port_user_full(user2, distance=d, degree=d) for user2 in (dset[d] & dset2[1])]
    return records #+ _group_member_records_include(logged_in_user, dset2[1] - c_users.union({logged_in_user}))


def connection_record(user2, user1, _distance=None, degree=None):
  if degree is None:
    degree = _degree(user2, user1)
  if _distance is None:
    _distance = degree # distance(user2, user1)
  record = vars(sm.get_port_user(user2, _distance))
  is_me = user2 == user1
  confirmed_url_date = user2['confirmed_url_date'] if user2['confirmed_url'] else None
  record.update({'me': is_me,
                 'degree': degree, 
                 'last_active': user2['init_date'],
                 'status': _invite_status(user2, user1),
                 'unread_message': None, # True/False
                 'first': user2['first_name'],
                 'last': port.last_name(user2['last_name'], record['distance']),
                 'confirmed_date': confirmed_url_date,
                 'trust_level': user2['trust_level'],
                 'trust_label': sm.trust_label[user2['trust_level']],
                })
  return record


### Not actually needed (with distance=degree) because direct connections of my direct connections will always be 2nd degree to me
# def _group_member_records_include(user, included_users):
#   from . import groups_server as g
#   import collections
#   fellow_members_to_group_names = collections.defaultdict(list)
#   for group_row in g.user_groups(user):
#     relevant_group_members = set(g.MyGroup.members_from_group_row(group_row)) & included_users
#     for user2 in relevant_group_members:
#       fellow_members_to_group_names[user2].append(group_row['name'])
#   return [sm.get_port_user_full(user2, user, port.UNLINKED, port.UNLINKED, fellow_members_to_group_names[user2]) 
#           for user2 in fellow_members_to_group_names.keys()]


def _group_member_records_exclude(user, excluded_users):
  from . import groups_server as g
  import collections
  fellow_members_to_group_names = collections.defaultdict(list)
  excluded_users.add(user)
  for group_row in g.user_groups(user):
    relevant_group_members = set(g.MyGroup.members_from_group_row(group_row, with_trust_level=True)) - excluded_users
    for user2 in relevant_group_members:
      fellow_members_to_group_names[user2].append(group_row['name'])
  return [sm.get_port_user_full(user2, user.get_id(), port.UNLINKED, port.UNLINKED, fellow_members_to_group_names[user2]) 
          for user2 in fellow_members_to_group_names.keys()]


def _invite_status(user2, user1):
  invites = app_tables.invites.search(user1=user1, user2=user2, origin=True, current=True)
  if len(invites) > 0:
    return "invite"
  else:
    inviteds = app_tables.invites.search(user1=user2, user2=user1, origin=True, current=True)
    if len(inviteds) > 0:
      return "invited"
    else:
      return ""
    

def get_relationships(user2, user1_id="", up_to_degree=3):
  """Returns ordered list of dictionaries"""
  user1 = sm.get_user(user1_id)
  dset = _get_connections(user1, up_to_degree)
  degree = _degree_from_dset(user2, dset)
  if degree == 0:
    return []
  elif degree == port.UNLINKED:
    return []
  elif degree == 1:
    conn = app_tables.connections.get(user1=user1, user2=user2, current=True)
    their_conn = app_tables.connections.get(user1=user2, user2=user1, current=True)
    return [{"via": False, 
             "whose": "my", 
             "desc": conn['relationship2to1'], 
             "date": conn['date_described'], 
             "child": None,
             "their": their_conn['relationship2to1'],
             "their_date": their_conn['date_described'],
             "their_name": user2['first_name'],
             "their_id": user2.get_id(),
            }]
  out = []
  dset2 = _get_connections(user2, degree-2)
  seconds = dset[2] & dset2[degree-2]
  for second in seconds:
    dset_second = _get_connections(second, 1)
    firsts = dset[1] & dset_second[1]
    for first in firsts:
      name = sm.name(first, distance=1)
      conn2 = app_tables.connections.get(user1=first, user2=second, current=True)
      conn1 = app_tables.connections.get(user1=user1, user2=first, current=True)
      out.append({"via": degree > 2,
                  "whose": f"{name}'s", 
                  "desc": conn2['relationship2to1'],
                  "date": conn2['date_described'],
                  "child": {"via": False,
                            "whose": "my", 
                            "desc": conn1['relationship2to1'],
                            "date": conn1['date_described'],
                            "child": None,
                           },
                 })
  return out 

  
@authenticated_callable
def load_invites(user_id=""):
#   from . import matcher as m
  from . import invites_server
  user = sm.get_user(user_id)
  rows = app_tables.invites.search(origin=True, user1=user, current=True)
  out = []
  for row in rows:
#     item = {k: row[k] for k in ['date', 'relationship2to1', 'date_described', 'guess', 'link_key', 'distance']}
#     if row['user2']:
#       item['user2'] = sm.get_port_user(row['user2'], user1_id=user.get_id(), simple=False)
#     if row['proposal']:
#       item['proposal'] = m.Proposal(row['proposal']).portable(user)
    out.append(invites_server.Invite.from_invite_row(row, portable=True, user_id=user.get_id()))
  return out

@authenticated_callable
@anvil.tables.in_transaction
def save_invites(items, user_id=""):
#   from . import matcher as m
  from . import invites_server
  from . import matcher
  user = sm.get_user(user_id)
  matcher.propagate_update_needed(user)
  for port_invite in items:
    invites_server.Invite(item).edit_invite()
#   link_keys = [item['link_key'] for item in items]
#   unmatched_rows = app_tables.invites.search(origin=True, user1=user, link_key=q.none_of(*link_keys), current=True)
#   for row in unmatched_rows:
#     row['current'] = False
#   for item in items:
#     if item.get('proposal'):
#       proposal = m.Proposal.get_by_id(item['proposal'].prop_id)
#       if proposal:
#         proposal.update(item['proposal'])   
#       else:
#         proposal = m.Proposal.add(user, item['proposal'])
#       item['proposal'] = proposal._row
#     if item.get('user2'):
#       item['user2'] = app_tables.users.get_by_id(item.get('user2').user_id)
#     row = app_tables.invites.get(origin=True, user1=user, link_key=item['link_key'], current=True)
#     if row:
#       row.update(**item)
#     else:
#       new_item = {'origin': True, 'user1': user}
#       new_item.update(item)
#       app_tables.invites.add_row(**new_item, current=True)


def remove_invite_pair(invite, invite_reply, user):
  try_removing_from_invite_proposal(invite, user)
  invite['current'] = False
  invite_reply['current'] = False

  
def _invited_item_to_row_dict(invited_item, user, distance=1):
  user2 = app_tables.users.get_by_id(invited_item['inviter_id'])
  now = sm.now()
  return dict(date=now,
              origin=False,
              user1=user,
              user2=user2,
              relationship2to1=invited_item['relationship'],
              date_described=now,
              guess=invited_item['phone_last4'],
              distance=distance,
              link_key=invited_item['link_key'],
             ) 


def try_adding_to_invite_proposal(invite, user):
  if invite['proposal']:
    from . import matcher as m
    proposal = m.Proposal(invite['proposal'])
    if proposal['current'] and user not in proposal['eligible_users']:
      proposal['eligible_users'] += [user]
      # Don't try to notify new_user invitee here because missing time_zone, first_name, and notif_settings

      
def try_removing_from_invite_proposal(invite, user):
  if invite['proposal']:
    from . import matcher as m
    proposal = m.Proposal(invite['proposal'])
    if user in proposal['eligible_users']:
      temp = proposal['eligible_users']
      temp.remove(user)
      proposal['eligible_users'] = temp
      
  
def try_connect(invite, invite_reply):
  from .invites_server import Invite
  if Invite.phone_match(invite['guess'], invite['user2']):
    try_adding_to_invite_proposal(invite, invite['user2'])
    already = app_tables.connections.search(user1=q.any_of(invite['user1'], invite['user2']), user2=q.any_of(invite['user1'], invite['user2']), current=True)
    if len(already) > 0:
      sm.warning(f"connection already exists, {dict(invite)}")
      return True
    app_tables.prompts.add_row(**_connected_prompt(invite, invite_reply))
    for i_row in [invite, invite_reply]:
      item = {k: i_row[k] for k in {"user1", "user2", "date", "relationship2to1", "date_described", "distance", "current"}}
      app_tables.connections.add_row(**item)
      i_row['current'] = False
    _clear_cached_connections()
    return True
  else:
    print(f"invite['guess'] doesn't match, {dict(invite)}, {invite['user2']['phone']}")
    return False
 

def _connected_prompt(invite, invite_reply):
  return dict(user=invite['user1'],
              spec={"name": "connected", "to_name": sm.name(invite['user2'], distance=invite['distance']), 
                    "to_id": invite['user2'].get_id(), "rel": invite_reply['relationship2to1'],},
              date=sm.now(),
              dismissed=False,
             )


@authenticated_callable
@anvil.tables.in_transaction
def save_relationship(item, user_id=""):
  user1 = sm.get_user(user_id)
  user2 = app_tables.users.get_by_id(item['user2_id'])
  row = app_tables.connections.get(user1=user1, user2=user2, current=True)
  row['relationship2to1'] = item['relationship']
  row['date_described'] = sm.now()
  return row['date_described']

  
@authenticated_callable
@anvil.tables.in_transaction
def disconnect(user2_id, user1_id=""):
  user1 = sm.get_user(user1_id)
  from . import matcher
  matcher.propagate_update_needed()
  user2 = app_tables.users.get_by_id(user2_id)
  if user2:
    r1to2 = app_tables.connections.get(user1=user1, user2=user2, current=True)
    r2to1 = app_tables.connections.get(user1=user2, user2=user1, current=True)
    if r1to2 and r2to1: 
      r1to2['current'] = False
      r2to1['current'] = False
      _clear_cached_connections()
      _remove_connection_prompts(user1, user2)
      return True
  return False
    
  
def _remove_connection_prompts(user1, user2):
  prompts = app_tables.prompts.search(user=user1, spec={'name': 'connected', 'to_id': user2.get_id()})
  for prompt in prompts:
    prompt.delete()
  prompts = app_tables.prompts.search(user=user2, spec={'name': 'connected', 'to_id': user1.get_id()})
  for prompt in prompts:
    prompt.delete()
    