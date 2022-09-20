from anvil.tables import in_transaction
import anvil.server
from . import invites
from . import server_misc as sm
from . import accounts
from . import parameters as p
from . import invite_gateway as ig
from .exceptions import RowMissingError, MistakenGuessError, InvalidInviteError, MistakenVisitError


@anvil.server.callable
def serve_invite_unauth(port_invite, method, kwargs):
  return _serve_invite(port_invite, method, kwargs, auth=False)


@sm.authenticated_callable
@in_transaction
def serve_invite(port_invite, method, kwargs):
  return _serve_invite(port_invite, method, kwargs, auth=True)


def _serve_invite(port_invite, method, kwargs, auth):
  print(f"invites_server: {method}({kwargs}) called on {port_invite}")
  invite = Invite(port_invite)
  errors = invite.relay(method, kwargs, auth=auth)
  return invite.portable(), errors
    

@anvil.server.callable
def load_from_link_key(link_key):
  """Return Invite
  
     Raise error if visitor is logged in and mistaken inviter guess
  """
  invite = _get_invite_from_link_key(link_key)
  user = sm.get_acting_user()
  if user:
    if user == invite.inviter:
      raise MistakenVisitError(p.CLICKED_OWN_LINK_ERROR)
    _handle_invitee_phone_match_check(invite, user)
  return invite.portable()


def _get_invite_from_link_key(link_key):
  try:
    return ig.get_invite_from_link_key(link_key)
  except RowMissingError:
    _handle_missing_invite_link_key(link_key)

    
def _handle_missing_invite_link_key(link_key):
  if ig.old_invite_row_exists(link_key):
    raise InvalidInviteError("This invite link is no longer active.")
  else:
    raise InvalidInviteError("Invalid invite link")


def _handle_invitee_phone_match_check(invite, user):
  try:
    _check_invitee_phone_match(invite, user)
  except MistakenGuessError as err:
    _handle_mistaken_inviter_guess_error(invite, err)


def _check_invitee_phone_match(invite, user):
  if user['phone'] and not phone_match(invite.inviter_guess, user):
    invite.invitee = user #for the sake of subsequent (out of transaction) _add_guess_fail_prompt(invite)
    raise MistakenGuessError(p.MISTAKEN_INVITER_GUESS_ERROR)


def _handle_mistaken_inviter_guess_error(invite, err):
  if err.args[0] == p.MISTAKEN_INVITER_GUESS_ERROR:
    _add_guess_fail_prompt(invite)
    invite.inviter['update_needed'] = True
  raise err


@in_transaction
def _add_guess_fail_prompt(invite):
  sm.add_invite_guess_fail_prompt(invite)


@anvil.server.callable
def respond_to_close_invite(port_invite):
  invite = _get_s_invite_and_check_validity(port_invite)
  user = sm.get_acting_user()
  if user:
    _try_to_save_response(invite, user)


def _get_s_invite_and_check_validity(port_invite):
  if port_invite.invalid_response():
    raise InvalidInviteError(", ".join(port_invite.invalid_response()))
  invite = Invite(port_invite)
  ig.ensure_correct_inviter_info(invite)
  _check_inviter_phone_match(invite)
  return invite


def _check_inviter_phone_match(invite):
  if not phone_match(invite.invitee_guess, invite.inviter):
    raise MistakenGuessError(f"You did not accurately provide the last 4 digits of {sm.name(invite.inviter)}'s confirmed phone number.")


def _try_to_save_response(invite, user):
  try:
    _save_response(invite, user)
  except MistakenGuessError as err:
    _handle_mistaken_inviter_guess_error(invite, err)


@in_transaction
def _save_response(invite, user):
  print(f"_save_response: ({invite.invite_id}, {invite.response_id}), {user['email']}")
  _check_invitee_phone_match(invite, user)
  invite.invitee = user
  ig.save_response(invite)
  if user['phone']:
    _try_connect(invite)

  
def _try_connect(invite):
  from . import matcher
  if ig.try_connect(invite):
    matcher.propagate_update_needed()


@sm.authenticated_callable
def load_invites(user_id=""):
  user = sm.get_acting_user(user_id)
  return ig.load_invites(user)


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
    validation_errors = self.invalid_invite()
    if validation_errors:
      raise InvalidInviteError("\n".join(validation_errors))
    if self.invitee:
      if not self.invitee['phone']:
        raise InvalidInviteError(f"{sm.name(self.invitee)} does not have a confirmed phone number.")
      elif not phone_match(self.inviter_guess, self.invitee):
        raise MistakenGuessError(f"The digits you entered do not match {sm.name(self.invitee)}'s confirmed phone number.")
      self.invitee['update_needed'] = True  # app_tables.users 
    else: # link invite
      user['last_invite'] = sm.now()
    self.link_key = "" if self.invitee else ig.new_link_key()
    ig.add_invite(self)

  # def edit_invite(self):
  #   errors = self.invalid_invite()
  #   if not errors:
  #     ig.update_invite(self)
  #   return errors
    
  def cancel(self):
    if self.invitee:
      self.invitee['update_needed'] = True
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

  def authorizes_signup(self):
    try:
      ig.check_id_and_link_key_and_ensure_correct_inviter(self)
    except RowMissingError:
      return False
    try:
      _check_inviter_phone_match(self)
    except MistakenGuessError:
      return False
    return True
    
  
  def register(self, user):
    if not user:
      sm.warning(f"visit called without user on {self}")
    ig.ensure_correct_inviter_info(self)
    _check_inviter_phone_match(self)
    _try_to_save_response(self, user)
    accounts.init_user_info(user)        

  def load(self):
    return ig.load_full_invite(self)
