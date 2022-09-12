import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .exceptions import RowMissingError
from . import invites
from . import server_misc as sm
from .exceptions import RowMissingError, ExpiredInviteError, InvalidInviteError


def get_invite_from_link_key(link_key, current=True):
  from . import invites_server
  invite_row = app_tables.invites.get(origin=True, link_key=link_key, current=current)
  if not invite_row:
    raise RowMissingError()
  port_invite = invites.Invite(
    link_key=link_key,
    invite_id=invite_row.get_id(),
    inviter=sm.get_port_user(invite_row['user1']),
    inviter_guess=invite_row['guess'],
    rel_to_inviter=invite_row['relationship2to1'],
  )
  return invites_server.Invite(port_invite)

def add_invite(invite):
  """Add row to invites table
  
  Side effect: add invite_id attribute to invite"""
  errors = []
  invite_row = _invite_row(invite, missing_ok=True)
  if not invite_row:
    now = sm.now()
    new_row = app_tables.invites.add_row(date=now,
                                         origin=True,
                                         distance=1,
                                         user1=invite.inviter,
                                         user2=invite.invitee,
                                         link_key=invite.link_key,
                                         current=True,
                                        )
    invite.invite_id = new_row.get_id()
    _edit_row(new_row, invite.inviter_guess, invite.rel_to_inviter, now)
  else:
    errors.append("This invite already exists.")
  return errors


def cancel_invite(invite):
  errors = []
  invite_row = _invite_row(invite, missing_ok=True)
  _try_removing_from_invite_proposal(invite_row, invite.invitee)
  if invite_row:
    invite_row['current'] = False
  else:
    errors.append(f"Invites row not found with id {invite.invite_id}")
  return errors


def cancel_response(invite):
  invite_row = _invite_row(invite)
  _try_removing_from_invite_proposal(invite_row, invite.invitee)
  errors = []
  response_row = _response_row(invite, missing_ok=True)
  if response_row:
    response_row['current'] = False
  else:
    errors.append(f"Response row not found")
  return errors


def _try_removing_from_invite_proposal(invite_row, invitee):
  if invite_row and invitee:
    from . import connections as c
    c.try_removing_from_invite_proposal(invite_row, invitee)


def _edit_row(row, guess, rel, now):
  row['guess'] = guess
  if rel != row['relationship2to1']:
    row['relationship2to1'] = rel
    row['date_described'] = now


def update_invite(invite):
  invite_row = _invite_row(invite)
  _edit_row(invite_row, invite.inviter_guess, invite.rel_to_inviter, sm.now())
    
    
def _invite_row(invite, missing_ok=False):
  return _row(invite, origin=True, missing_ok=missing_ok)


def _response_row(invite, missing_ok=False):
  return _row(invite, origin=False, missing_ok=missing_ok)


def _row(invite, origin, missing_ok=False):
  row_id = invite.invite_id if origin else invite.response_id
  row = None
  if row_id:
    row = app_tables.invites.get_by_id(row_id)
  elif invite.link_key:
    row = app_tables.invites.get(origin=origin, link_key=invite.link_key, current=True)
  elif invite.inviter and invite.invitee:
    user1 = invite.inviter if origin else invite.invitee
    user2 = invite.invitee if origin else invite.inviter
    row = app_tables.invites.get(origin=origin, user1=user1, user2=user2, current=True)
  else:
    raise(RowMissingError(f"Not enough information to retrieve {'invite' if origin else 'response'} row."))
  if not missing_ok and not row:
    raise(RowMissingError(f"No such {'invite' if origin else 'response'} row."))
  return row


def load_full_invite(invite):
  """Side effect: update invite object from data"""
  invite_row = _invite_row(invite, missing_ok=True)
  if invite_row:
    _load_invite(invite, invite_row)
    response_row = _response_row(invite, missing_ok=True)
    if response_row:
      _load_response(invite, response_row)

      
def _load_invite(invite, invite_row):
  invite.invite_id = invite_row.get_id()
  invite.inviter = invite_row['user1']
  invite.inviter_guess = invite_row['guess']
  invite.rel_to_inviter = invite_row['relationship2to1']

  
def _load_response(invite, response_row):
  invite.response_id = response_row.get_id()
  invite.invitee = response_row['user1']
  invite.invitee_guess = response_row['guess']
  invite.rel_to_invitee = response_row['relationship2to1']      


def old_invite_row_exists(link_key):
  return bool(len(app_tables.invites.search(origin=True, link_key=link_key, current=False)))


def save_invitee(invite, user):
  from . import connections as c
  invite_row = _invite_row(invite)
  if invite_row['user2'] and invite_row['user2'] != invite.invitee:
    sm.warning(f"invite['user2'] being overwritten, {user['email']}, {dict(invite_row)}, {invite.invite_id}")
  invite_row['user2'] = invite.invitee
  c.try_adding_to_invite_proposal(invite_row, invite.invitee)
  if invite.response_id:
    response_row = _response_row(invite)
    response_row['user1'] = invite.invitee


def save_response(invite):
  """Side effect: update invite object with response_id if new response"""
  now = sm.now()
  response_row = _response_row(invite, missing_ok=True)
  if not response_row:
    response_row = app_tables.invites.add_row(date=now,
                                              origin=False,
                                              distance=1,
                                              user1=invite.invitee,
                                              user2=invite.inviter,
                                              link_key=invite.link_key,
                                              current=True,
                                             )
    invite.response_id = response_row.get_id()
  _edit_row(response_row, invite.invitee_guess, invite.rel_to_invitee, now)

  
def try_connect(invite):
  from . import connections as c
  invite_row = _invite_row(invite)
  response_row = _response_row(invite)
  return c.try_connect(invite_row, response_row)


def from_invite_row(invite_row, user_id=""):
  user = sm.get_acting_user(user_id)
  port_invite = invites.Invite(invite_id=invite_row.get_id(),
                               inviter=sm.get_port_user(invite_row['user1'], user1=user),
                               rel_to_inviter=invite_row['relationship2to1'],
                               inviter_guess=invite_row['guess'],
                               link_key=invite_row['link_key'],
                               invitee=sm.get_port_user(invite_row['user2'], user1=user),
                              )
  return port_invite
  