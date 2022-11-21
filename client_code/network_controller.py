import operator
from . import glob
from . import helper as h
from . import groups
from . import portable as port
import anvil.server


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
    host_id = group['hosts'][0]
    subtext = f"(host: {glob.users[host_id].name})"
  return dict(key=group['name'], value=groups.Group(group['name'], group.group_id), subtext=subtext)
  


def get_create_user_items():
  """Return list with 1st---2nd""" # add pending connections to front
  user_id = glob.logged_in_user_id
  up_to_degree = 3 if glob.trust_level >= 3 else 1
  name_items = _get_sorted_name_items(user_id, up_to_degree)
  starred_name_list = [item['key'] for item in name_items if item['value'].starred] # ensures sort order
  return name_items, starred_name_list


def _get_sorted_name_items(user_id, up_to_degree):
  user_profiles = _get_my_connections(user_id, up_to_degree)
  name_items = [u.name_item() for u in user_profiles]
  name_items.sort(key=operator.itemgetter('subtext', 'key'))
  return name_items


def get_relationships(user2_id):
  """Returns ordered list of dictionaries"""
  user1_id = glob.logged_in_user_id
  degree = glob.users[user2_id].degree
  if degree in [0, port.UNLINKED]:
    return []
  elif degree == 1:
    return [_direct_relationship_dict(user1_id, user2_id, with_their=True)]
  else:
    return _indirect_relationship_dicts(user1_id, user2_id, degree)


def _direct_relationship_dict(user1_id, user2_id, with_their=False):
  conn = _get_connection(user1_id, user2_id)
  out = {"via": False,
         "whose": "my", 
         "desc": conn['relationship2to1'], 
         "date": conn['date_described'], 
         "child": None,
        }
  if with_their:
    out.update(_direct_relationship_their_dict(user1_id, user2_id))
  return out


def _direct_relationship_their_dict(user1_id, user2_id):
  their_conn = _get_connection(user2_id, user1_id)
  return {
    "their": their_conn['relationship2to1'],
    "their_date": their_conn['date_described'],
    "their_name": glob.users[user2_id]['first'],
    "their_id": user2_id,
  }


def _indirect_relationship_dicts(user1_id, user2_id, degree):
  out = []
  dset1 = _get_connection_ids(user1_id, 2)
  dset2 = _get_connection_ids(user2_id, degree-2, include_reverse=True)
  for second in (dset1[2] & dset2[degree-2]):
    dset_second = _get_connection_ids(second, 1)
    for first in (dset1[1] & dset_second[1]):
      out.append(_indirect_relationship_dict(user1_id, first, second, degree))
  return out


def _indirect_relationship_dict(user1_id, first, second, degree):
  via_str, via_id = _indirect_relationship_via(second, degree)
  conn2 = _get_connection(first, second)
  return {"via": via_str,
          "via_id": via_id,
          "whose": f"{glob.users[first].name}'s",
          "whose_id": first,
          "desc": conn2['relationship2to1'],
          "date": conn2['date_described'],
          "child": None, #_direct_relationship_dict(user1_id, first),
         }


def _indirect_relationship_via(second, degree):
  if degree > 3:
    return " [name hidden]'s", None
  elif degree > 2:
    return f" {glob.users[second].name}'s ", second
  else:
    return "", None


def _get_connection(user1_id, user2_id):
  results = [conn for conn in glob.connections
             if (conn['user1_id'] == user1_id and conn['user2_id'] == user2_id)]
  return results[0] if results else None


@anvil.server.portable_class
class MyGroupMember(port.UserProfile):
  def __init__(self, member_id, group_id, guest_allowed=False):
    self._init_user_profile_attributes(member_id)
    self.group_id = group_id
    self.guest_allowed = guest_allowed
    
  def _init_user_profile_attributes(self, member_id):
    user_profile = glob.users[member_id]
    for key in user_profile.__dict__:
      self.__setattr__(key, user_profile.__dict__[key])   
