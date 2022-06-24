import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .exceptions import RowMissingError
from . import invites
from . import server_misc as sm


def add_invite(invite):
  """Add row to invites table
  
  Side effect: add invite_id attribute to invite"""
  invite_row, errors = _invite_row(invite)
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
    
  
def _edit_row(row, guess, rel, now):
  row['guess'] = guess
  if rel != row['relationship2to1']:
    row['relationship2to1'] = rel
    row['date_described'] = now


def update_invite(invite):
  invite_row, errors = _invite_row(invite)
  errors = _edit_row(invite_row, invite.inviter_guess, invite.rel_to_inviter, sm.now())
    
    
def _invite_row(invite):
  return _row(invite, origin=True)


def _response_row(invite):
  return _row(invite, origin=False)


def _row(invite, origin):
  row_id = invite.invite_id if origin else invite.response_id
  row = None
  errors = []
  if row_id:
    row = app_tables.invites.get_by_id(row_id)
  elif invite.link_key:
    row = app_tables.invites.get(origin=origin, link_key=invite.link_key, current=True)
  elif invite.inviter and invite.invitee:
    user1 = invite.inviter if origin else invite.invitee
    user2 = invite.invitee if origin else invite.inviter
    row = app_tables.invites.get(origin=origin, user1=user1, user2=user2, current=True)
  else:
    errors.append(f"Not enough information to retrieve {'invite' if origin else 'response'} row.")
  return row, errors


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
  