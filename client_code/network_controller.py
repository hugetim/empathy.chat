import operator
import anvil.server as server
from . import glob
from . import helper as h
from . import groups
from . import portable as port


def not_me(user_id):
  return user_id and user_id != glob.logged_in_user_id


def _get_connection_ids(user_id, up_to_degree=3, include_reverse=False):
  """Return dictionary from degree to set of connections"""
  out = {0: {user_id}}
  prev = set()
  for d in range(0, up_to_degree):
    prev.update(out[d])
    current = _get_direct_connections_of(out[d], include_reverse)
    out[d+1] = current - prev
  return out


def _get_direct_connections_of(user_ids_set, include_reverse=False):
  id1 = 'user1_id'
  id2 = 'user2_id'
  out = {row[id2] for row in glob.connections if row[id1] in user_ids_set}
  if include_reverse:
    out.update({row[id1] for row in glob.connections if row[id2] in user_ids_set})
  return out


def _get_their_connections(user_id):
  dset2 = _get_connection_ids(user_id, 1)
  return [glob.users[id] for id in dset2[1]]


def _get_my_connections(user_id, up_to_degree=3):
  dset = _get_connection_ids(user_id, up_to_degree)
  records = []
  c_user_ids = set()
  for d in range(1, up_to_degree+1):
    records += [glob.users[id] for id in dset[d]]
    c_user_ids.update(dset[d])
  return records + _group_member_records_exclude(user_id, c_user_ids)


def _group_member_records_exclude(user_id, excluded_user_ids):
  excluded_user_ids.add(user_id)
  relevant_group_member_ids = _fellow_group_member_ids() - excluded_user_ids
  return [glob.users[user2_id] for user2_id in relevant_group_member_ids]


def _fellow_group_member_ids():
  fellow_member_ids = set()
  for group in glob.my_groups:
    fellow_member_ids.update({member_dict['member_id'] for member_dict in group.members})
  for group in glob.their_groups.values():
    fellow_member_ids.update(set(group.members))
  return fellow_member_ids


def get_connections(user_id):
  profiles = (_get_their_connections(user_id) if not_me(user_id) 
              else _get_my_connections(glob.logged_in_user_id))
  return sorted(profiles, key=lambda u: (u.distance_str_or_groups, h.reverse_compare(u.last_active)))


def get_create_group_items():
  items = []
  for g in glob.my_groups:
    items.append(_group_item(g, my_group=True))
  for g in glob.their_groups.values():
    items.append(_group_item(g))
  return sorted(items, key=lambda item:(item['subtext'] + item['key']))


def _group_item(group, my_group=False):
  if my_group:
    subtext = "(host: me)"
  else:
    host_id = g['hosts'][0]
    subtext = f"(host: {glob.users[host_id].name})"
  return dict(key=g['name'], value=groups.Group(g['name'], g.group_id), subtext=subtext)
  


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
    conn = _get_connection(user1_id, user2_id)
    their_conn = _get_connection(user2_id, user1_id)
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
  dset2 = _get_connection_ids(user2_id, degree-2, include_reverse=True)
  seconds = dset[2] & dset2[degree-2]
  for second in seconds:
    dset_second = _get_connection_ids(second, 1)
    firsts = dset[1] & dset_second[1]
    for first in firsts:
      conn2 = _get_connection(first, second)
      conn1 = _get_connection(user1_id, first)
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
             if (conn['user1_id'] == user1_id and conn['user2_id'] == user2_id)]
  return results[0] if results else None


class MyGroupMember(port.UserProfile):
  def __init__(self, member_id, group_id, guest_allowed=False):
    self._init_user_profile_attributes(member_id)
    self.group_id = group_id
    self.guest_allowed = guest_allowed
    
  def _init_user_profile_attributes(self, member_id):
    user_profile = glob.users[member_id]
    for key in user_profile.__dict__:
      self.__setattr__(key, user_profile.__dict__[key])   
