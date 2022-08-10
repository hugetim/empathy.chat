import anvil.server as server
from . import glob
from . import helper as h
from . import groups


def not_me(user_id):
  return user_id and user_id != glob.logged_in_user_id


def _get_connection_ids(user_id, up_to_degree=3):
  """Return dictionary from degree to set of connections"""
  degree1s = {row['user_id2'] for row in glob.connections if row['user_id1'] == user_id}
  out = {0: {user_id}, 1: degree1s}
  prev = {user_id}
  for d in range(1, up_to_degree):
    prev.update(out[d])
    current = {row['user_id2'] for row in glob.connections if row['user_id1'] in out[d]}
    out[d+1] = current - prev
  return out


def _get_their_connections(user_id):
  dset2 = _get_connection_ids(user_id, 1)
  return [glob.users[id] for id in dset2[1]]


def _get_my_connections(user_id, up_to_degree=3):
  dset = _get_connection_ids(user_id, up_to_degree)
  records = []
  c_user_ids = set()
  for d in range(1, up_to_degree+1):
    records += [glob.users[id] for id in dset[d]] # sm.get_port_user_full(user2, logged_in_user, distance=d, degree=d) for user2 in 
    c_user_ids.update(dset[d])
  return records + _group_member_records_exclude(user_id, c_user_ids)


def _group_member_records_exclude(user_id, excluded_user_ids):
  excluded_user_ids.add(user_id)
  fellow_members_to_group_names = _group_members_to_group_names_exclude(excluded_user_ids)
  return [glob.users[user_id2] for user_id2 in fellow_members_to_group_names.keys()] #not using group names


def _group_members_to_group_names_exclude(excluded_user_ids):
  import collections
  fellow_members_to_group_names = collections.defaultdict(list)
  # if glob.trust_level < 1:
  #   return {}
  for group in glob.their_groups.values():
    # if glob.trust_level < 2:
    #   if not g.guest_allowed_in_group(user, group_row):
    #     continue
    relevant_group_member_ids = set(group.members) - excluded_user_ids
    for user_id2 in relevant_group_member_ids:
      fellow_members_to_group_names[user_id2].append(group.name)
  return fellow_members_to_group_names


def get_connections(user_id):
  if not_me(user_id):
    return _get_their_connections(user_id)
  else:
    return _get_my_connections(glob.logged_in_user_id)


def get_create_group_items():
  items = []
  for g in glob.my_groups:
    subtext = "(host: me)"
    items.append(dict(key=g['name'], value=groups.Group(g['name'], g.group_id), subtext=subtext))
  for g in glob.their_groups.values():
    host_id = g['hosts'][0]
    subtext = f"(host: {glob.users[host_id].name})"
    items.append(dict(key=g['name'], value=groups.Group(g['name'], g.group_id), subtext=subtext))
  print(3)
  return sorted(items, key=lambda item:(item['subtext'] + item['key']))


def _group_member_items_exclude(user_id, excluded_user_ids):
  excluded_user_ids.add(user_id)
  fellow_members_to_group_names = _group_members_to_group_names_exclude(excluded_user_ids)
  items = [glob.users[user_id2].name_item() for user2 in fellow_members_to_group_names.keys()]
  return sorted(items, key = lambda name_item:(name_item['subtext'] + name_item['key']))


def get_create_user_items():
  """Return list with 1st---2nd""" # add pending connections to front
  user_id = glob.logged_in_user_id
  up_to_degree = 3 if glob.trust_level >= 3 else 1
  users = _get_my_connections(user_id, up_to_degree)
  # dset = _get_connection_ids(user_id, up_to_degree)
  # dset[2] = [other for other in dset[2] if glob.user[other]['trust_level'] >= 3]
  # dset[3] = [other for other in dset[3] if glob.user[other]['trust_level'] >= 3]
  # items = {}
  # degree_set = [1, 2, 3] if my_trust_level >= 3 else [1]
  # c_users = set()
  # for degree in degree_set:
  #   # change to distance=distance(user2, user1) or equivalent once properly implement distance
  #   items[degree] = [glob.users[other].name_item() for other in dset[degree]]
  #   items[degree].sort(key=lambda user_item: user_item['key'])
  #   c_users.update(dset[degree])
  # group_member_items = _group_member_items_exclude(glob.logged_in_user_id, c_users)
  name_items = [u.name_item() for u in users]
  starred_name_list = [u.name for u in users if u.starred]
  return name_items, starred_name_list
