import operator
import anvil.server as server
from . import glob
from . import helper as h
from . import groups
from . import portable as port


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
  if glob.trust_level < 1:
    return {}
  for group in glob.my_groups:
    # if glob.trust_level < 2:
    #   if not g.guest_allowed_in_group(user, group_row):
    #     continue
    relevant_group_member_ids = set([u.user_id for u in group.members]) - excluded_user_ids
    for user_id2 in relevant_group_member_ids:
      fellow_members_to_group_names[user_id2].append(group.name)
  for group in glob.their_groups.values():
    # if glob.trust_level < 2:
    #   if not g.guest_allowed_in_group(user, group_row):
    #     continue
    relevant_group_member_ids = set(group.members) - excluded_user_ids
    for user_id2 in relevant_group_member_ids:
      fellow_members_to_group_names[user_id2].append(group.name)
  return fellow_members_to_group_names


def get_connections(user_id):
  profiles = (_get_their_connections(user_id) if not_me(user_id) 
              else _get_my_connections(glob.logged_in_user_id))
  return sorted(profiles, key=lambda u: (u.distance_str_or_groups, h.reverse_compare(u.last_active)))


def get_create_group_items():
  items = []
  for g in glob.my_groups:
    subtext = "(host: me)"
    items.append(dict(key=g['name'], value=groups.Group(g['name'], g.group_id), subtext=subtext))
  for g in glob.their_groups.values():
    host_id = g['hosts'][0]
    subtext = f"(host: {glob.users[host_id].name})"
    items.append(dict(key=g['name'], value=groups.Group(g['name'], g.group_id), subtext=subtext))
  return sorted(items, key=lambda item:(item['subtext'] + item['key']))


def get_create_user_items():
  """Return list with 1st---2nd""" # add pending connections to front
  user_id = glob.logged_in_user_id
  up_to_degree = 3 if glob.trust_level >= 3 else 1
  users = _get_my_connections(user_id, up_to_degree)
  name_items = [u.name_item() for u in users]
  name_items.sort(key=operator.itemgetter('subtext', 'key'))
  starred_name_list = [item['key'] for item in name_items if item['value'].starred]
  return name_items, starred_name_list


def get_relationships(user2_id, up_to_degree=3):
  """Returns ordered list of dictionaries"""
  user1_id = glob.logged_in_user_id
  user2 = glob.users[user2_id]
  degree = user2.degree
  if degree == 0:
    return []
  elif degree == port.UNLINKED:
    return []
  elif degree == 1:
    conn = _get_connections(user1_id, first)
    [conn] = [conn for conn in glob.connections 
              if (conn['user_id1'] == user1_id and conn['user_id2'] == user2_id)]
    [their_conn] = [conn for conn in glob.connections
                    if (conn['user_id1'] == user2_id and conn['user_id2'] == user1_id)]
    return [{"via": False, 
             "whose": "my", 
             "desc": conn['relationship2to1'], 
             "date": conn['date_described'], 
             "child": None,
             "their": their_conn['relationship2to1'],
             "their_date": their_conn['date_described'],
             "their_name": user2['first'],
             "their_id": user2_id,
            }]
  out = []
  dset = _get_connection_ids(user1_id, 2)
  dset2 = _get_connection_ids(user2_id, degree-2)
  seconds = dset[2] & dset2[degree-2]
  for second in seconds:
    dset_second = _get_connection_ids(second, 1)
    firsts = dset[1] & dset_second[1]
    for first in firsts:
      conn2 = _get_connections(first, second)
      conn1 = _get_connections(user1_id, first)
      if degree > 3:
        via = " [name hidden]'s"
      elif degree > 2:
        via = f" {glob.users[second].name}'s "
      else:
        via = ""
      out.append({"via": via,
                  "whose": f"{glob.users[first].name}'s", 
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


def _get_connection(user1_id, user2_id):
  results = [conn for conn in glob.connections
             if (conn['user_id1'] == user1_id and conn['user_id2'] == user2_id)]
  return results[0] if results else None