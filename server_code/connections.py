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
  degree_set = [1, 2] if user['trust_level'] >= 3 else [1]
  for degree in degree_set:
    # change to distance=distance(user2, user1) or equivalent once properly implement distance
    items[degree] = [sm.get_port_user(other, distance=degree).name_item() for other in dset[degree]]
    items[degree].sort(key=lambda user_item: user_item[0])
  if user['trust_level'] >= 3 and items[2]:
    return items[1] + ["---"] + items[2] 
  else:
    return items[1]


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


def member_close_connections(user):
  """Returns list of users"""
  degree1s = _get_connections(user, 1)[1]
  return [user2 for user2 in degree1s
          if user2['trust_level'] >= 3 and distance(user2, user, 1) == 1]
  
    
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
  """Returns dict w/ port.User attrs as str keys, plus: degree, last_active, status, unread_message"""
  degree = _degree(user2, user1)
  _distance = distance(user2, user1)
  record = vars(sm.get_port_user(user2, _distance))
  record.update({'degree': degree, 
                 'last_active': user2['last_login'],
                 'status': _invite_status(user2, user1),
                 'unread_message': None, # True/False
                })
  return record


def _invite_status(user2, user1):
  invites = app_tables.invites.search(user1=user1, user2=user2, origin=True)
  if len(invites) > 0:
    return "invite"
  else:
    inviteds = app_tables.invites.search(user1=user2, user2=user1, origin=True)
    if len(inviteds) > 0:
      return "invited"
    else:
      return ""
    

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
      their_conn = app_tables.connections.get(user1=user2, user2=user1)
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
    #[{"via": True, "whose": "", "desc": "", "date": ""}] if degree <= 2 else 
    out = []
    dset2 = _get_connections(user2, degree-2, include_zero=True)
    seconds = dset[2] & dset2[degree-2]
    for second in seconds:
      dset_second = _get_connections(second, 1)
      firsts = dset[1] & dset_second[1]
      for first in firsts:
        name = sm.name(first, distance=1)
        conn2 = app_tables.connections.get(user1=first, user2=second)
        conn1 = app_tables.connections.get(user1=user1, user2=first)
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
def cancel_invite(link_key, user_id=""):
  user = sm.get_user(user_id)
  row = app_tables.invites.get(link_key=link_key, user1=user)
  if row:
    row.delete()

    
@authenticated_callable
@anvil.tables.in_transaction
def invite_user(item, user_id=""):
  user1 = sm.get_user(user_id)
  user2 = app_tables.users.get_by_id(item['user_id'])
  now = sm.now()
  if item['phone_last4'] == user2['phone'][-4:]:
    app_tables.invites.add_row(date=now,
                               origin=True,
                               user1=user1,
                               user2=user2,
                               relationship2to1=item['relationship'],
                               date_described=now,
                               guess=item['phone_last4'],
                               distance=1,
                               link_key="",
                              )
    return item
  else:
    return None

@authenticated_callable
@anvil.tables.in_transaction
def add_invite(item, user_id=""):
  user = sm.get_user(user_id)
  now = sm.now()
  link_key = sm.random_code(num_chars=7)
  app_tables.invites.add_row(date=now,
                             origin=True,
                             user1=user,
                             relationship2to1=item['relationship'],
                             date_described=now,
                             guess=item['phone_last4'],
                             distance=1,
                             link_key=link_key,
                            )
  return {"link_key": link_key,
          "invite_url": f"{p.URL}#?invite={link_key}"}


@authenticated_callable
def load_invites(user_id=""):
  from . import matcher as m
  user = sm.get_user(user_id)
  rows = app_tables.invites.search(origin=True, user1=user)
  out = []
  for row in rows:
    item = {k: row[k] for k in ['date', 'relationship2to1', 'date_described', 'guess', 'link_key', 'distance']}
    if row['user2']:
      item['user2'] = sm.get_port_user(user2, user1_id=user.get_id(), simple=False)
    if row['proposal']:
      item['proposal'] = m.Proposal(row['proposal']).portable(user)
    out.append(item)
  return out

@authenticated_callable
@anvil.tables.in_transaction
def save_invites(items, user_id=""):
  from . import matcher as m
  user = sm.get_user(user_id)
  link_keys = [item['link_key'] for item in items]
  unmatched_rows = app_tables.invites.search(origin=True, user1=user, link_key=q.none_of(*link_keys))
  for row in unmatched_rows:
    row.delete()
  for item in items:
    if item.get('proposal'):
      proposal = m.Proposal.get_by_id(item['proposal'].prop_id)
      if proposal:
        proposal.update(item['proposal'])   
      else:
        proposal = m.Proposal.add(user, item['proposal'])
      item['proposal'] = proposal._row
    if item.get('user2'):
      item['user2'] = sm.get_user(item.get('user2').user_id, require_auth=False)
    row = app_tables.invites.get(origin=True, user1=user, link_key=item['link_key'])
    if row:
      row.update(**item)
    else:
      new_item = {'origin': True, 'user1': user}
      new_item.update(item)
      app_tables.invites.add_row(**new_item)


@anvil.server.callable
def invite_visit(link_key, user_id=""):
  invite = app_tables.invites.get(origin=True, link_key=link_key)
  if invite:
    user2 = app_tables.users.get_by_id(user_id) if user_id else None
    if user2:
      invite['user2'] = user2
    anvil.server.session['invite_link_key'] = link_key
    item = {'link_key': link_key}
    item['relationship1to2'] = invite['relationship2to1']
    item['inviter'] = invite['user1']['first_name']
    item['inviter_id'] = invite['user1'].get_id()
    invite_reply = app_tables.invites.get(origin=False, link_key=link_key)
    if invite_reply:
      item['relationship'] = invite_reply['relationship2to1']
      item['phone_last4'] = invite_reply['guess']
      invite_reply['user1'] = user2
    else:
      item['relationship'] = ""
      item['phone_last4'] = ""
    return item
  else:
    return False

  
@anvil.server.callable
@anvil.tables.in_transaction
def invite_visit_register(link_key, user):
  invite = app_tables.invites.get(origin=True, link_key=link_key)
  invite_reply = app_tables.invites.get(origin=False, link_key=link_key)
  if invite and invite_reply:
    anvil.users.force_login(user)
    invite.update(user2=user)
    invite_reply.update(user1=user)
  else:
    print("Warning: invite_visit_register failed", link_key, user.get_id())

  
@anvil.server.callable
@anvil.tables.in_transaction
def add_invited(item):
  user = anvil.users.get_user()
  return _add_invited(item, user)


def _add_invited(item, user):
  user2 = app_tables.users.get_by_id(item['inviter_id'])
  if item['phone_last4'] == user2['phone'][-4:]:
    now = sm.now()
    link_key = item['link_key']
    info = dict(date=now,
                origin=False,
                user1=user,
                user2=user2,
                relationship2to1=item['relationship'],
                date_described=now,
                guess=item['phone_last4'],
                distance=1,
                link_key=link_key,
               )
    invite_reply = app_tables.invites.get(origin=False, link_key=link_key)
    if invite_reply:
      invite_reply.update(**info)
    else:
      app_tables.invites.add_row(**info)
    if user:
      invite = app_tables.invites.get(origin=True, user1=user2, link_key=link_key)
      if invite:
        invite.update(user2=user)
        if invite['proposal']:
          from . import matcher as m
          proposal = m.Proposal(invite['proposal'])
          if user not in proposal.eligible_users:
            proposal.eligible_users += [user]
    return item
  else:
    return None

  
@authenticated_callable
@anvil.tables.in_transaction
def connect_invited(item, user_id=""):
  user = sm.get_user(user_id)
  phone_match = _add_invited(item, user)
  if phone_match:
    user2 = app_tables.users.get_by_id(item['inviter_id'])
    invite = app_tables.invites.get(origin=True, user1=user2, user2=user, link_key="")
    invite_reply = app_tables.invites.get(origin=False, user1=user, user2=user2, link_key="")
    if invite and invite_reply:
      connect(invite, invite_reply)
      return phone_match
  return False
  
        
def connect(invite, invite_reply):
  if invite['proposal']:
    from . import matcher as m
    proposal = m.Proposal(invite['proposal'])
    invited = invite['user2']
    if invited not in proposal.eligible_users:
      proposal.eligible_users += [invited]
  app_tables.prompts.add_row(**_connected_prompt(invite, invite_reply))
  for row in [invite, invite_reply]:
    item = {k: row[k] for k in {"user1", "user2", "date", "relationship2to1", "date_described", "distance"}}
    app_tables.connections.add_row(starred=False, **item)
    row.delete()
 

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
  user2 = sm.get_user(item['user2_id'], require_auth=False)
  row = app_tables.connections.get(user1=user1, user2=user2)
  row['relationship2to1'] = item['relationship']
  row['date_described'] = sm.now()
  return row['date_described']

  
@anvil.server.callable
def cancel_invited(item):
  row = app_tables.invites.get(link_key=item['link_key'],
                               relationship2to1=item['relationship'],
                               user2=app_tables.users.get_by_id(item['inviter_id']),
                              )
  if row:
    row.delete()

    
@authenticated_callable
@anvil.tables.in_transaction
def disconnect(user2_id, user1_id=""):
  user1 = sm.get_user(user1_id)
  user2 = sm.get_user(user2_id, require_auth=False)
  if user2:
    r1to2 = app_tables.connections.get(user1=user1, user2=user2)
    r2to1 = app_tables.connections.get(user1=user2, user2=user1)
    if r1to2 and r2to1: 
      r1to2.delete()
      r2to1.delete()
      return True
  return False
    