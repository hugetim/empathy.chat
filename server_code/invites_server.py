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
from . import parameters as p


@anvil.server.callable
@anvil.tables.in_transaction
def serve_invite_unauth(port_invite, method, kwargs):
  from . import matcher
  matcher.propagate_update_needed()
  return _serve_invite(port_invite, method, kwargs, auth=False)


@sm.authenticated_callable
@anvil.tables.in_transaction
def serve_invite(port_invite, method, kwargs):
  from . import matcher
  matcher.propagate_update_needed()
  return _serve_invite(port_invite, method, kwargs, auth=True)


def _serve_invite(port_invite, method, kwargs, auth):
  print(f"invites_server: {method}({kwargs}) called on {port_invite}")
  invite = Invite(port_invite)
  errors = invite.relay(method, kwargs, auth=auth)
  return invite.portable(), errors


class Invite(invites.Invite):
  no_auth_methods = ['visit', 'register', 'respond']
  
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

  def relay(self, method, kwargs=None, auth=True):
    if not kwargs:
      kwargs = {}
    if (method in self.no_auth_methods) or auth:
      return getattr(self, method)(**kwargs)
    else:
      return ["Not authorized."]
  
  def add(self, user_id=""):
    """Side effect: Add invites row"""
    user = sm.get_user(user_id)
    self.inviter = user
    errors = self.invalid_invite()
    if self.invitee:
      if not self.invitee['phone']:
        errors.append(f"{sm.name(self.invitee)} does not have a confirmed phone number.")
      elif not Invite.phone_match(self.inviter_guess, self.invitee):
        errors.append(f"The digits you entered do not match {sm.name(self.invitee)}'s confirmed phone number.")
    else:
      user['last_invite'] = sm.now()
    if not errors:
      self.link_key = "" if self.invitee else sm.random_code(num_chars=7)
      invite_row, errors = self._invite_row()
      if not invite_row:
        now = sm.now()
        new_row = app_tables.invites.add_row(date=now,
                                             origin=True,
                                             distance=1,
                                             user1=self.inviter,
                                             user2=self.invitee,
                                             link_key=self.link_key,
                                             current=True,
                                            )
        self.invite_id = new_row.get_id()
        self._edit_row(new_row, self.inviter_guess, self.rel_to_inviter, now)
      else:
        errors.append("This invite already exists.")
    return errors

  @staticmethod
  def phone_match(last4, user):
    return last4 == user['phone'][-4:]
  
  def _edit_row(self, row, guess, rel, now):
    row['guess'] = guess
    if rel != row['relationship2to1']:
      row['relationship2to1'] = rel
      row['date_described'] = now

  def edit_invite(self):
    errors = self.invalid_invite()
    if not errors:
      invite_row, errors = self._invite_row()
      self._edit_row(invite_row, self.inviter_guess, self.rel_to_inviter, sm.now())
    return errors
    
  def cancel(self, invite_row=None):
    if not invite_row:
      invite_row, errors = self._invite_row()
    else:
      errors = []
    if invite_row:
      if self.invitee:
        from . import connections as c
        c.try_removing_from_invite_proposal(invite_row, self.invitee)
      invite_row['current'] = False
    else:
      errors.append(f"Invites row not found with id {self.invite_id}")
    self.cancel_response() # Not finding a response_row is not an error here
    self._clear()
    return errors

  def cancel_response(self):
    from . import connections as c
    invite_row, _ = self._invite_row()
    if invite_row and self.invitee:
      c.try_removing_from_invite_proposal(invite_row, self.invitee)
    response_row, errors = self._response_row()
    if response_row:
      response_row['current'] = False
    else:
      errors.append(f"Response row not found")
    self._clear()
    return errors
  
  def _clear(self):
    for key, value in vars(self).items():
      if key in ['inviter', 'invitee']:
        self[key] = None
      else:
        self[key] = ""
    
  def _invite_row(self):
    return self._row(origin=True)
  
  def _response_row(self):
    return self._row(origin=False)
 
  def _row(self, origin):
    row_id = self.invite_id if origin else self.response_id
    row = None
    errors = []
    if row_id:
      row = app_tables.invites.get_by_id(row_id)
    elif self.link_key:
      row = app_tables.invites.get(origin=origin, link_key=self.link_key, current=True)
    elif self.inviter and self.invitee:
      user1 = self.inviter if origin else self.invitee
      user2 = self.invitee if origin else self.inviter
      row = app_tables.invites.get(origin=origin, user1=user1, user2=user2, current=True)
    else:
      errors.append(f"Not enough information to retrieve {'invite' if origin else 'response'} row.")
    return row, errors

  def visit(self, user, register=False):
    """Assumes only self.link_key known (unless register)
    
       Side effects: set invite['user2'] if visitor is logged in,
       likewise for invite_reply['user1'] if it exists"""
    invite_row, errors = self._invite_row()
    if invite_row:
      errors += self._load_invite(invite_row)
      if user:
        errors += self._try_adding_invitee(user, invite_row)
      response_row = app_tables.invites.get(origin=False, link_key=self.link_key, current=True)
      if response_row:
        if self.invitee:
          response_row['user1'] = self.invitee
          if register:
            sm.init_user_info(user)
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
  
  def _load_response(self, response_row):
    errors = []
    self.response_id = response_row.get_id()
    self.invitee = response_row['user1']
    self.invitee_guess = response_row['guess']
    self.rel_to_invitee = response_row['relationship2to1']
    return errors

  def _try_adding_invitee(self, user, invite_row):
    from . import connections as c
    errors = []
    self.invitee = user
    if user['phone'] and not Invite.phone_match(self.inviter_guess, user):
      errors += [p.MISTAKEN_INVITER_GUESS_ERROR]
      sm.add_invite_guess_fail_prompt(self)
      errors += self.cancel(invite_row)
    else:
      if invite_row['user2'] and invite_row['user2'] != self.invitee:
        print("Warning: invite['user2'] being overwritten")
      invite_row['user2'] = self.invitee
      c.try_adding_to_invite_proposal(invite_row, self.invitee)
    return errors

  def respond(self, user_id=""):
    """Returns list of error strings"""
    user = sm.get_user(user_id)
    invite_row, errors = self._invite_row()
    if user:
      errors += self._try_adding_invitee(user, invite_row)
      if errors:
        return errors
    now = sm.now()
    errors += self.invalid_response()
    if errors:
      return errors
    if not Invite.phone_match(self.invitee_guess, self.inviter):
      errors.append(f"You did not accurately provide the last 4 digits of {sm.name(self.inviter)}'s confirmed phone number.")
      return errors
    response_row, errors = self._response_row()
    if not response_row:
      response_row = app_tables.invites.add_row(date=now,
                                                origin=False,
                                                distance=1,
                                                user1=self.invitee,
                                                user2=self.inviter,
                                                link_key=self.link_key,
                                                current=True,
                                               )
    self._edit_row(response_row, self.invitee_guess, self.rel_to_invitee, now)
    if self.invitee and self.invitee['phone']:
      from . import connections as c
      self.connection_successful = c.try_connect(invite_row, response_row)
      if not self.connection_successful:
        print("Warning: unexpected failed connect")
    return errors

  def load(self):
    invite_row, errors = self._invite_row()
    if invite_row:
      errors += self._load_invite(invite_row)
      response_row, _ = self._response_row()
      if response_row:
        errors += self._load_response(response_row)
    return errors

  @staticmethod
  def from_invite_row(invite_row, portable=False, user_id=""):
    port_invite = invites.Invite(invite_id=invite_row.get_id(),
                                 inviter=sm.get_port_user(invite_row['user1']),
                                 rel_to_inviter=invite_row['relationship2to1'],
                                 inviter_guess=invite_row['guess'],
                                 link_key=invite_row['link_key'],
                                 invitee=sm.get_port_user(invite_row['user2'], user1_id=user_id),
                                )
    return port_invite if portable else Invite(port_invite)

  
#   def serve(self):
#     errors = []
#     invite_row = self._invite_row()
#     if invite_row:
#       errors += self._sync_invite(invite_row)
#     elif self.not_yet_added and self.ready_to_add:
#       new_self, add_errors = self.add(self.inviter.user_id if self.inviter else "")
#       self.update(new_self)
#       errors += add_errors
#     else:
#       errors += "No matching invite found."
#     response_row = self._response_row()
#     if response_row:
#       errors += self._sync_response(response_row)
#     elif not self.response_id and self.response_ready:
#       errors += self._add_response()
#     elif self.response_id:
#       errors.append("Response row not found")
#     return self, errors

  

  
