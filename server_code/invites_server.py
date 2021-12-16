import anvil.users
import anvil.google.auth, anvil.google.drive, anvil.google.mail
from anvil.google.drive import app_files
import anvil.secrets
import anvil.email
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from . import invites
from . import server_misc as sm


@anvil.server.callable
@anvil.tables.in_transaction
def serve_invite(port_invite, method, kwargs):
  invite = Invite(port_invite)
  errors = getattr(invite, method)(**kwargs)
  return invite.portable(), errors


class Invite(invites.Invite):
  def __init__(self, port_invite):
    self.update(port_invite)
    self._convert_port_user('inviter')
    self._convert_port_user('invitee')

  def _convert_port_user(self, port_user_attr_name):
    port_user_attr = getattr(self, port_user_attr_name)
    if port_user_attr:
      setattr(self, port_user_attr_name, port_user_attr.s_user)
 
  def portable(self):
    port = invites.Invite()
    port.update(self)
    port.inviter = sm.get_port_user(self.inviter)
    port.invitee = sm.get_port_user(self.invitee)
    return port
  
  def add(self, user_id=""):
    """Side effect: Add invites row"""
    user = sm.get_user(user_id)
    self.inviter = user
    errors = self.invalid_invite()
    if self.invitee:
      if not self.invitee['phone']:
        errors.append(f"{sm.name(self.invitee)} does not have a confirmed phone number.")
      elif not Invite.phone_match(self.inviter_guess, self.invitee):
        errors.append(f"You did not accurately provide the last 4 digits of {sm.name(self.invitee)}'s confirmed phone number.")
    if not errors:
      self.link_key = "" if self.invitee else sm.random_code(num_chars=7)
      if not self.invite_row():
        now = sm.now()
        new_row = app_tables.invites.add_row(date=now,
                                             origin=True,
                                             distance=1,
                                             user1=self.inviter,
                                             user2=self.invitee,
                                             link_key=self.link_key,
                                            )
        self.invite_id = new_row.get_id()
        self._edit_invite_row(new_row, now)
      else:
        errors.append("This invite already exists.")
    return errors

  @staticmethod
  def phone_match(last4, user):
    return last4 == user['phone'][-4:]
  
  def _edit_invite_row(self, invite_row, now):
    invite_row.update(guess=self.inviter_guess,
                      relationship2to1=self.rel_to_inviter,
                      date_described=now,
                     )

  def cancel(self):
    errors = []
    invite_row = self.invite_row()
    if invite_row:
      invite_row.delete()
    else:
      errors.append(f"Invites row not found with id {self.invite_id}")
    new_self, other_errors = self.cancel_response()
    errors += other_errors
    self._clear()
    return errors

  def cancel_response(self):
    errors = []
    response_row = self.response_row()
    if response_row:
      response_row.delete()
    else:
      errors.append(f"Response row not found")
    self._clear()
    return self, errors
  
  def _clear(self):
    for key, value in vars(self).items():
      if key in ['inviter', 'invitee']:
        self[key] = None
      else:
        self[key] = ""
    
  def invite_row(self):
    return self._row(origin=True)
  
  def response_row(self):
    return self._row(origin=False)
 
  def _row(self, origin):
    row_id = self.invite_id if origin else self.response_id
    if row_id:
      return app_tables.invites.get_by_id(row_id)
    elif self.link_key:
      return app_tables.invites.get(origin=origin, link_key=self.link_key)
    elif self.inviter and self.invitee:
      user1 = self.inviter if origin else self.invitee
      user2 = self.invitee if origin else self.inviter
      return app_tables.invites.get(origin=origin, user1=user1, user2=user2)
    else:
      print(f"Warning: not enough information to retrieve {'invite' if origin else 'response'} row.")
      return None

  def visit(self, user):
    """Assumes only self.link_key known
    
       Side effects: set invite['user2'] if visitor is logged in,
       likewise for invite_reply['user1'] if it exists"""
    errors = []
    invite_row = self.invite_row()
    if invite_row:
      errors += self._load_invite(invite_row)
      if user:
        errors += self._try_adding_invitee(user, invite_row)
      response_row = app_tables.invites.get(origin=False, link_key=self.link_key)
      if response_row:
        errors += self._load_response(response_row)
    else:
      errors.append("Invalid invite link")
    return errors
        
  def _load_invite(self, invite_row):
    errors = []
    self.invite_id = invite_row.get_id()
    self.inviter = invite_row['user1']
    self.inviter_guess = invite_row['guess']
    self.rel_to_inviter = invite_row['relationship2to1']
    return errors

  def _try_adding_invitee(self, user, invite_row):
    errors = []
    self.invitee = user
    if user['phone'] and not Invite.phone_match(self.inviter_guess, user):
      errors.append("The inviter did not accurately provide the last 4 digits of your phone number.")
      sm.add_invite_guess_fail_prompt(self)
      cancel_errors = self.cancel()
      errors += cancel_errors
    else:
      if invite_row['user2'] and invite_row['user2'] != user:
        print("Warning: invite['user2'] being overwritten")
      invite_row['user2'] = user
    return errors
  
  def _add_response(self):
    """Returns list of error strings"""
    import server_misc as sm
    now = sm.now()
    new_row = app_tables.invites.add_row(date=now,
                                     origin=False,
                                     date_described=now,
                                     distance=1,
                                    )
    self._sync_response(new_row)
    return []
  
#   def _sync_user(self, attr_port_user_name, row, column_name, check_auth=False, load_only=False):
#     import server_misc as sm
#     attr_port_user = getattr(self, attr_port_user_name)
#     if check_auth:
#       user_to_check = attr_port_user.s_user if attr_port_user else row[column_name]
#       if user_to_check:
#         sm.get_user(user_to_check.get_id(), require_auth=True)
#     if attr_port_user and not load_only:
#       row[column_name] = attr_port_user.s_user
#     elif row[column_name]:
#       setattr(self, attr_port_user_name, sm.get_port_user(row[column_name]))
 
#   def _sync(self, attr_name, row, column_name, date_updated_column_name="", load_only=False):
#     import server_misc as sm
#     attr = getattr(self, attr_name)
#     if attr and not load_only:
#       if row[column_name] != attr:
#         row[column_name] = attr
#         if date_updated_column_name:
#           row[date_updated_column_name] = sm.now()
#     elif row[column_name]:
#       setattr(self, attr_name, row[column_name])
 
#   def _sync_response(self, response_row, check_auth=True, load_only=False):
#     """Returns list of error strings
    
#     Assumes response_row exists (is not None)"""
#     if load_only:
#       check_auth = False
#     errors = []
#     self.response_id = response_row.get_id()
#     self._sync_user('invitee', response_row, 'user1', load_only=load_only, check_auth=check_auth)
#     self._sync_user('inviter', response_row, 'user2', load_only=load_only)
#     self._sync('invitee_guess', response_row, 'guess', load_only=load_only)
#     self._sync('rel_to_invitee', response_row, 'relationship2to1', load_only=load_only, date_updated_column_name='date_described')
#     self._sync('link_key', invite_row, 'link_key', load_only=load_only)
#     return errors

    
#   def serve(self):
#     errors = []
#     invite_row = self.invite_row()
#     if invite_row:
#       errors += self._sync_invite(invite_row)
#     elif self.not_yet_added and self.ready_to_add:
#       new_self, add_errors = self.add(self.inviter.user_id if self.inviter else "")
#       self.update(new_self)
#       errors += add_errors
#     else:
#       errors += "No matching invite found."
#     response_row = self.response_row()
#     if response_row:
#       errors += self._sync_response(response_row)
#     elif not self.response_id and self.response_ready:
#       errors += self._add_response()
#     elif self.response_id:
#       errors.append("Response row not found")
#     return self, errors

  
#   @staticmethod
#   def from_invited(self, inviter_id, user_id=""):
#     pass
  
