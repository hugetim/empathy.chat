import anvil.tables
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


quick_c_fetch = q.fetch_only('distance', 'date', 'relationship2to1', 'date_described', 'user2', user1=q.fetch_only('first_name'))


def _get_connections(user, up_to_degree=3, cache_override=False, output_conn_list=False):
  """Return dictionary from degree to set of connections"""
  if up_to_degree not in range(1, 98):
    sm.warning(f"_get_connections(user, {up_to_degree}) not expected")
  if not cache_override: # and user == sm.get_acting_user():
    return _cached_get_connections(user, up_to_degree)
  conn_rows = {}
  conn_rows[0] = app_tables.connections.search(quick_c_fetch, user1=user, current=True)
  degree1s = {row['user2'] for row in conn_rows[0]}
  out = {0: {user}, 1: degree1s}
  prev = {user}
  for d in range(1, up_to_degree):
    prev.update(out[d])
    conn_rows[d] = app_tables.connections.search(quick_c_fetch, user1=q.any_of(*out[d]), current=True)
    current = {row['user2'] for row in conn_rows[d]}
    out[d+1] = current - prev
  if not output_conn_list:
    return out
  else:
    return out, _get_connections_list(conn_rows, up_to_degree)


def _get_connections_list(conn_rows, up_to_degree):
  connections_list = []
  for d in range(0, up_to_degree):
    connections_list += [_port_conn_row(row, d) for row in conn_rows[d]]
  return connections_list


def _port_conn_row(row, distance):
  # assumes distance = degree
  rel = row['relationship2to1'] if distance <= 1 else ""
  return dict(user1_id=row['user1'].get_id(), user2_id=row['user2'].get_id(), relationship2to1=rel,
              date=row['date'], date_described=row['date_described'], distance=row['distance'],
             )


_cached_connections = {}
_cached_up_to = {}

def _cached_get_connections(user, up_to_degree):
  global _cached_connections
  global _cached_up_to
  if user not in _cached_connections or up_to_degree > _cached_up_to[user]:
    _cached_connections[user] = _get_connections(user, up_to_degree=up_to_degree, cache_override=True)
    _cached_up_to[user] = up_to_degree
  return {key: _cached_connections[user][key].copy() for key in range(up_to_degree+1)}


def _clear_cached_connections():
  global _cached_connections
  global _cached_up_to
  _cached_connections = {}
  _cached_up_to = {}

  
def member_close_connections(user):
  """Returns list of users"""
  degree1s = _get_connections(user, 1)[1]
  return [user2 for user2 in degree1s
          if user2['trust_level'] >= 3 and distance(user2, user, up_to_distance=1) == 1]
  

def _degree(user2, user1, up_to_degree=3):
  """Returns port.UNLINKED if no degree <= up_to_degree found"""
  if user1 in _cached_connections and up_to_degree <= _cached_up_to[user1]:
    return _degrees([user1], user2, up_to_degree)[user1]
  else:
    return _degrees([user2], user1, up_to_degree)[user2]

  
def _degree_from_dset(user2, dset):
  for d in dset:
    if user2 in dset[d]:
      return d
  return port.UNLINKED
  

def _degrees(user2s, user1, up_to_degree=3):
  """Returns port.UNLINKED if no degree <= up_to_degree found"""
  out = {}
  if user2s:
    dset = _get_connections(user1, up_to_degree)
    for user2 in set(user2s):
      out[user2] = 0 if user2==user1 else _degree_from_dset(user2, dset)
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


@anvil.tables.in_transaction(relaxed=True)
def init_connections(user=None):
  with TimerLogger("  init_connections", format="{name}: {elapsed:6.3f} s | {msg}") as timer:
    logged_in_user = user if user else sm.get_acting_user()
    up_to_degree = 3
    dset, connections_list = _get_connections(logged_in_user, up_to_degree, cache_override=True, output_conn_list=True)
    timer.check('_get_connections')
    records, c_users, starred_users = _get_records_and_c_users(logged_in_user, dset, up_to_degree)
    timer.check('_get_records_and_c_users')
    users_dict, their_groups_dict = _profiles_and_their_groups(logged_in_user, c_users, records, starred_users)
    return users_dict, connections_list, their_groups_dict


def _get_records_and_c_users(logged_in_user, dset, up_to_degree):
  from . import network_gateway as ng
  records = [_connection_record(logged_in_user, logged_in_user)]
  starred_users = set(ng.starred_users(logged_in_user))
  connected_users = set()
  for d in range(1, up_to_degree+1):
    records += [_connection_record(user2, logged_in_user, _distance=d, degree=d, starred=(user2 in starred_users)) 
                for user2 in dset[d]]
    connected_users.update(dset[d])
  return records, connected_users, starred_users


def _profiles_and_their_groups(user, c_users, records, starred_users):
  members_to_group_names, their_groups_dict = _group_info(user)
  records += [_connection_record(user2, user, port.UNLINKED, port.UNLINKED, starred=(user2 in starred_users)) 
              for user2 in set(members_to_group_names.keys()) - c_users.union({user})]
  invite_dict = _get_invite_dict(user)
  users_dict = {record['user_id']: _get_port_profile(record, members_to_group_names, invite_dict) for record in records}
  return users_dict, their_groups_dict


def _group_info(user):
  import collections
  members_to_group_names = collections.defaultdict(list)
  their_groups_dict = {}
  for group_row, group_members in _group_and_members(user):
    for user2 in group_members:
      members_to_group_names[user2].append(group_row['name'])
    if user not in group_row['hosts']:
      their_groups_dict[group_row.get_id()] = _port_group(group_row, group_members)
  return members_to_group_names, their_groups_dict


def _group_and_members(user):
  from . import groups_server as g
  for group_row in g.user_groups(user):
    group_members = {u for u in g.allowed_members_from_group_row(group_row, user)}
    yield (group_row, group_members)
    

def _port_group(group_row, group_members):
  from . import groups
  return groups.Group(name=group_row['name'],
                      group_id=group_row.get_id(),
                      members=[u.get_id() for u in group_members],
                      hosts=[u.get_id() for u in group_row['hosts']],
                     )


def _get_port_profile(record, members_to_group_names, invite_dict):
  from . import relationship as rel
  user = record.pop('user')
  relationship = rel.Relationship(distance=record['distance'])
  record.update({
    'common_group_names': members_to_group_names[user],
    'how_empathy': user['how_empathy'],
    'profile': user['profile'],
    'profile_updated': user['profile_updated'],
    'profile_url': user['profile_url'] if relationship.profile_url_visible else "",
    'status': _invite_status(user, invite_dict) if record['distance'] > 1 else "",
  })
  return port.UserProfile(**record)


def _connection_record(user2, user1, _distance=None, degree=None, starred=None):
  if degree is None:
    degree = _degree(user2, user1)
  if _distance is None:
    _distance = degree # distance(user2, user1)
  record = vars(sm.get_port_user(user2, _distance, user1=user1, starred=starred))
  relationship = record.pop('relationship')
  is_me = user2 == user1
  record.update({'me': is_me,
                 'degree': degree, 
                 'last_active': user2['init_date'],
                 'unread_message': None, # True/False
                 'first': user2['first_name'],
                 'last': port.last_name(user2['last_name'], relationship),
                 'url_confirmed_date': user2['url_confirmed_date'],
                 'trust_level': user2['trust_level'],
                 'trust_label': accounts.trust_label[user2['trust_level']],
                 'user': user2,
                })
  return record


def _get_invite_dict(user):
  return dict(users_inviting={row['user2'] for row in app_tables.invites.search(user1=user, origin=True, current=True)},
              users_invited_by={row['user1'] for row in app_tables.invites.search(user2=user, origin=True, current=True)},
             )


def _invite_status(user2, invite_dict):
  if user2 in invite_dict['users_inviting']:
    return "invite"
  else:
    if user2 in invite_dict['users_invited_by']:
      return "invited"
    else:
      return ""


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


def try_adding_to_invite_proposal(invite_row, invitee_user):
  from .request_gateway import requests_by_invite_row
  user_id = invitee_user.get_id()
  for rr in requests_by_invite_row(invite_row, records=True):
    if user_id not in rr.entity.eligible_users:
      rr.entity.eligible_users += [user_id]
      rr.save()
      # Don't try to notify new_user invitee here because missing time_zone, first_name, and notif_settings

      
def try_removing_from_invite_proposal(invite_row, invitee_user):
  from .request_gateway import requests_by_invite_row
  user_id = invitee_user.get_id()
  for rr in requests_by_invite_row(invite_row, records=True):
    if user_id in rr.entity.eligible_users:
      rr.entity.eligible_users.remove(user_id)
      rr.save()
      
  
def try_connect(invite, invite_reply):
  from .invites_server import phone_match
  if phone_match(invite['guess'], invite['user2']):
    try_adding_to_invite_proposal(invite, invite['user2'])
    if _already_connected(invite):
      sm.warning(f"connection already exists, {dict(invite)}, {invite['user1']['email']} to {invite['user2']['email']}")
      return True
    app_tables.prompts.add_row(**_connected_prompt(invite, invite_reply))
    _transform_invite_rows_to_connections(invite, invite_reply)
    return True
  else:
    print(f"invite['guess'] doesn't match, {dict(invite)}, {invite['user2']['phone']}")
    return False


def _already_connected(invite):
  already = app_tables.connections.search(quick_c_fetch, user1=q.any_of(invite['user1'], invite['user2']), user2=q.any_of(invite['user1'], invite['user2']), current=True)
  return len(already) > 0


def _transform_invite_rows_to_connections(invite, invite_reply):
  for i_row in [invite, invite_reply]:
    item = {k: i_row[k] for k in {"user1", "user2", "date", "relationship2to1", "date_described", "distance", "current"}}
    app_tables.connections.add_row(**item)
    i_row['current'] = False
  _clear_cached_connections()
  

def _connected_prompt(invite, invite_reply):
  return dict(user=invite['user1'],
              spec={"name": "connected", "to_name": sm.name(invite['user2'], distance=invite['distance']), 
                    "to_id": invite['user2'].get_id(), "rel": invite_reply['relationship2to1'],},
              date=sm.now(),
              dismissed=False,
             )


@authenticated_callable
@anvil.tables.in_transaction(relaxed=True)
def save_relationship(item, user_id=""):
  user1 = sm.get_acting_user(user_id)
  user2 = sm.get_other_user(item['user2_id'])
  row = app_tables.connections.get(user1=user1, user2=user2, current=True)
  row['relationship2to1'] = item['relationship'].strip()
  row['date_described'] = sm.now()
  return row['date_described']

  
@authenticated_callable
def disconnect(user2_id, user1_id=""):
  from . import matcher
  user1 = sm.get_acting_user(user1_id)
  user2 = sm.get_other_user(user2_id)
  out = _disconnect(user2, user1)
  matcher.propagate_update_needed()
  return out


@anvil.tables.in_transaction
def _disconnect(user2, user1):
  if user2:
    r1to2 = app_tables.connections.get(user1=user1, user2=user2, current=True)
    r2to1 = app_tables.connections.get(user1=user2, user2=user1, current=True)
    if r1to2 and r2to1:
      with anvil.tables.batch_update:
        r1to2['current'] = False
        r2to1['current'] = False
      _clear_cached_connections()
      _remove_connection_prompts(user1, user2)
      return True
  return False
    
  
def _remove_connection_prompts(user1, user2):
  prompts1 = app_tables.prompts.search(q.fetch_only('dismissed'), user=user1, spec={'name': 'connected', 'to_id': user2.get_id()})
  prompts2 = app_tables.prompts.search(q.fetch_only('dismissed'), user=user2, spec={'name': 'connected', 'to_id': user1.get_id()})
  with anvil.tables.batch_delete:
    for prompt in prompts1:
      prompt.delete()
    for prompt in prompts2:
      prompt.delete()
    