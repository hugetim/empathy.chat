import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from . import server_misc as sm
from . import accounts
from .server_misc import authenticated_callable
from . import portable as port
from . import parameters as p
from . import helper as h
from anvil_extras.server_utils import timed
from anvil_extras.logging import TimerLogger
  

def _get_connections(user, up_to_degree=3, cache_override=False, output_conn_list=False):
  """Return dictionary from degree to set of connections"""
  if up_to_degree not in range(0, 98):
    sm.warning(f"_get_connections(user, {up_to_degree}) not expected")
  if not cache_override and user == anvil.users.get_user():
    return _cached_get_connections(user, up_to_degree)
  conn_rows = {}
  conn_rows[0] = app_tables.connections.search(user1=user, current=True)
  degree1s = {row['user2'] for row in conn_rows[0]}
  out = {0: {user}, 1: degree1s}
  if user in out[1]:
    sm.warning(f"user in out[1]")
  prev = {user}
  for d in range(1, up_to_degree):
    prev.update(out[d])
    conn_rows[d] = app_tables.connections.search(user1=q.any_of(*out[d]), current=True)
    current = {row['user2'] for row in conn_rows[d]}
    out[d+1] = current - prev
  if not output_conn_list:
    return out
  else:
    connections_list = []
    for d in range(0, up_to_degree):
      connections_list += [_port_conn_row(row, d) for row in conn_rows[d]]
    return out, connections_list


def _port_conn_row(row, distance):
  # assumes distance = degree
  rel = row['relationship2to1'] if distance <= 1 else ""
  return dict(user1_id=row['user1'].get_id(), user2_id=row['user2'].get_id(), relationship2to1=rel,
              date=row['date'], date_described=row['date_described'], distance=row['distance'],
             )


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


def get_connected_users(user, up_to_degree):
  dset = _get_connections(user, up_to_degree)
  c_users = set()
  for d in range(1, up_to_degree+1):
    c_users.update(dset[d])
  return c_users


def init_connections():
  logged_in_user = sm.get_acting_user()
  up_to_degree = 3
  dset, connections_list = _get_connections(logged_in_user, up_to_degree, cache_override=True, output_conn_list=True)
  records = [connection_record(logged_in_user, logged_in_user)]
  c_users = set()
  for d in range(1, up_to_degree+1):
    records += [connection_record(user2, logged_in_user, _distance=d, degree=d) for user2 in dset[d]]
    c_users.update(dset[d])
  users_dict, their_groups_dict = _profiles_and_their_groups(logged_in_user, c_users, records, connections_list)
  return users_dict, connections_list, their_groups_dict


def _profiles_and_their_groups(user, c_users, records, connections_list):
  from . import groups_server as g
  from . import groups
  import collections
  their_groups_dict = {}
  members_to_group_names = collections.defaultdict(list)
  trust_level = user['trust_level']
  if trust_level >= 1:
    for group_row in g.user_groups(user):
      if trust_level < 1 or (trust_level < 2 and not g.guest_allowed_in_group(user, group_row)):
        group_members = group_row['hosts']
      else:
        group_members = {u for u in g.members_from_group_row(group_row)
                        if (u['trust_level'] >= 2 
                            or (u['trust_level'] >= 1 and g.guest_allowed_in_group(u, group_row))
                            )
                        }
      if user not in group_row['hosts']:
        their_groups_dict[group_row.get_id()] = groups.Group(name=group_row['name'],
                                                            group_id=group_row.get_id(),
                                                            members=[u.get_id() for u in group_members],
                                                            hosts=[u.get_id() for u in group_row['hosts']],
                                                            )
      for user2 in group_members:
        members_to_group_names[user2].append(group_row['name'])
  records += [connection_record(user2, user, port.UNLINKED, port.UNLINKED) 
              for user2 in set(members_to_group_names.keys()) - c_users.union({user})]
  users_dict = {record['user_id']: _get_port_profile(record, connections_list, members_to_group_names) for record in records}
  return users_dict, their_groups_dict


def _get_port_profile(record, connections_list, members_to_group_names):
  from . import relationship as rel
  user = sm.get_other_user(record['user_id'])
  relationship = rel.Relationship(distance=record['distance'])
  record.update({
    'common_group_names': members_to_group_names[user],
    'how_empathy': user['how_empathy'],
    'profile': user['profile'],
    'profile_updated': user['profile_updated'],
    'profile_url': user['profile_url'] if relationship.profile_url_visible else "",
  })
  return port.UserProfile(**record)


def connection_record(user2, user1, _distance=None, degree=None):
  if degree is None:
    degree = _degree(user2, user1)
  if _distance is None:
    _distance = degree # distance(user2, user1)
  record = vars(sm.get_port_user(user2, _distance, user1=user1))
  relationship = record.pop('relationship')
  is_me = user2 == user1
  record.update({'me': is_me,
                 'degree': degree, 
                 'last_active': user2['init_date'],
                 'status': _invite_status(user2, user1),
                 'unread_message': None, # True/False
                 'first': user2['first_name'],
                 'last': port.last_name(user2['last_name'], relationship),
                 'url_confirmed_date': user2['url_confirmed_date'],
                 'trust_level': user2['trust_level'],
                 'trust_label': accounts.trust_label[user2['trust_level']],
                })
  return record
  

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
    

@authenticated_callable
def load_invites(user_id=""):
#   from . import matcher as m
  from . import invite_gateway
  user = sm.get_acting_user(user_id)
  rows = app_tables.invites.search(origin=True, user1=user, current=True)
  out = []
  for row in rows:
#     item = {k: row[k] for k in ['date', 'relationship2to1', 'date_described', 'guess', 'link_key', 'distance']}
#     if row['user2']:
#       item['user2'] = sm.get_port_user(row['user2'], user1=user, simple=False)
#     if row['proposal']:
#       item['proposal'] = m.Proposal(row['proposal']).portable(user)
    out.append(invite_gateway.from_invite_row(row, user_id=user.get_id()))
  return out


def remove_invite_pair(invite, invite_reply, user):
  try_removing_from_invite_proposal(invite, user)
  invite['current'] = False
  invite_reply['current'] = False

  
def _invited_item_to_row_dict(invited_item, user, distance=1):
  user2 = sm.get_other_user(invited_item['inviter_id'])
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
  from .invites_server import phone_match
  if phone_match(invite['guess'], invite['user2']):
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
  user1 = sm.get_acting_user(user_id)
  user2 = sm.get_other_user(item['user2_id'])
  row = app_tables.connections.get(user1=user1, user2=user2, current=True)
  row['relationship2to1'] = item['relationship']
  row['date_described'] = sm.now()
  return row['date_described']

  
@authenticated_callable
@anvil.tables.in_transaction
def disconnect(user2_id, user1_id=""):
  user1 = sm.get_acting_user(user1_id)
  from . import matcher
  matcher.propagate_update_needed()
  user2 = sm.get_other_user(user2_id)
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
    