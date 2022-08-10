import anvil.server as server
from . import glob
from . import helper as h


def _get_connections(user_id, up_to_degree=3):
  """Return dictionary from degree to set of connections"""
  degree1s = {row['user_id2'] for row in glob.connections if row['user_id1'] == user_id}
  out = {0: {user_id}, 1: degree1s}
  prev = {user_id}
  for d in range(1, up_to_degree):
    prev.update(out[d])
    current = {row['user_id2'] for row in glob.connections if row['user_id1'] in out[d]}
    out[d+1] = current - prev
  return out


def _get_my_connections(user_id):
  up_to_degree = 3
  dset = _get_connections(user_id, up_to_degree)
  records = []
  c_user_ids = set()
  for d in range(1, up_to_degree+1):
    records += [id for id in dset[d]] # sm.get_port_user_full(user2, logged_in_user, distance=d, degree=d) for user2 in 
    c_user_ids.update(dset[d])
  return records #+ _group_member_records_exclude(logged_in_user, c_users)


def get_connections(user_id):
  #assume me
  return _get_my_connections(user_id)
