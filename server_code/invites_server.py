from anvil.tables import in_transaction
import anvil.server
from . import invites
from . import server_misc as sm
from . import accounts
from . import parameters as p
from . import invite_gateway as ig


@anvil.server.callable
@in_transaction
def serve_invite_unauth(port_invite, method, kwargs):
  from . import matcher
  matcher.propagate_update_needed()
  return _serve_invite(port_invite, method, kwargs, auth=False)


@sm.authenticated_callable
@in_transaction
def serve_invite(port_invite, method, kwargs):
  from . import matcher
  matcher.propagate_update_needed()
  return _serve_invite(port_invite, method, kwargs, auth=True)


def _serve_invite(port_invite, method, kwargs, auth):
  print(f"invites_server: {method}({kwargs}) called on {port_invite}")
  invite = Invite(port_invite)
  errors = invite.relay(method, kwargs, auth=auth)
  return invite.portable(), errors


def phone_match(last4, user):
  return last4 == user['phone'][-4:]


class Invite(invites.Invite):
  no_auth_methods = ['visit', 'register', 'respond']
  
  def __init__(self, port_invite):
    self.update(port_invite)
    self._convert_port_user('inviter')
    self._convert_port_user('invitee')

  def _convert_port_user(self, port_user_attr_name):
    port_user_attr = getattr(self, port_user_attr_name)
    if port_user_attr:
      setattr(self, port_user_attr_name, sm.get_other_user(port_user_attr.user_id))
 
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
    user = sm.get_acting_user(user_id)
    self.inviter = user
    errors = self.invalid_invite()
    if self.invitee:
      if not self.invitee['phone']:
        errors.append(f"{sm.name(self.invitee)} does not have a confirmed phone number.")
      elif not phone_match(self.inviter_guess, self.invitee):
        errors.append(f"The digits you entered do not match {sm.name(self.invitee)}'s confirmed phone number.")
    else:
      user['last_invite'] = sm.now()
    if not errors:
      self.link_key = "" if self.invitee else sm.random_code(num_chars=7)
      errors = ig.add_invite(self)
    return errors

  def edit_invite(self):
    errors = self.invalid_invite()
    if not errors:
      ig.update_invite(self)
    return errors
    
  def cancel(self):
    errors = ig.cancel_invite(self)
    self.cancel_response() # Not finding a response_row is not an error here
    self._clear()
    return errors

  def cancel_response(self):
    errors = ig.cancel_response(self)
    self._clear()
    return errors
  
  def _clear(self):
    for key, value in vars(self).items():
      if key in ['inviter', 'invitee']:
        self[key] = None
      else:
        self[key] = ""
  
  def visit(self, user, register=False):
    """Assumes only self.link_key known (unless register)
    
       Side effects: set invite['user2'] if visitor is logged in,
       likewise for invite_reply['user1'] if it exists"""
    errors = []
    ig.load_full_invite(self)
    if self.invite_id:
      if user:
        if user == self.inviter:
          errors += [p.CLICKED_OWN_LINK_ERROR]
          return errors
        errors += self._try_adding_invitee(user)
        if errors:
          return errors
        ig.save_invitee(self, user)
        if self.invitee and self.invitee['phone']:
          errors += self._try_connect()
        if register:
          accounts.init_user_info(user)        
    else:
      if ig.old_invite_row_exists(self.link_key):
        errors.append("This invite link is no longer active.")
      else:
        errors.append("Invalid invite link")
    return errors

  def _try_adding_invitee(self, user):
    errors = []
    self.invitee = user
    if user['phone'] and not phone_match(self.inviter_guess, user):
      errors += [p.MISTAKEN_INVITER_GUESS_ERROR]
      sm.add_invite_guess_fail_prompt(self)
      errors += self.cancel()
    return errors

  def _try_connect(self):
    errors = []
    connection_successful = ig.try_connect(self)
    if not connection_successful:
      errors.append(f"{sm.name(self.inviter)} did not accurately provide the last 4 digits of your confirmed phone number.")
    return errors
  
  def respond(self, user_id=""):
    """Returns list of error strings"""
    user = sm.get_acting_user(user_id)
    errors = []
    if user:
      errors += self._try_adding_invitee(user)
      if errors:
        return errors
      ig.save_invitee(self, user)
    errors += self.invalid_response()
    if errors:
      return errors
    if not phone_match(self.invitee_guess, self.inviter):
      errors.append(f"You did not accurately provide the last 4 digits of {sm.name(self.inviter)}'s confirmed phone number.")
      return errors
    ig.save_response(self)
    if self.invitee and self.invitee['phone']:
      errors += self._try_connect()
    return errors

  def load(self):
    return ig.load_full_invite(self)
