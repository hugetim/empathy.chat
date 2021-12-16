import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from . import helper as h
from . import parameters as p


class Invites(h.AttributeToKey):
  def __init__(self):
    self.invites = []

  def to_data(self):
    return self.invites
    
  def __len__(self):
    return len(self.invites)
    
  def save(self):
    invites_data = [invite.to_data() for invite_data in self.invites]
    anvil.server.call('save_invites', invites_data)
    
  def load(self):
    invites_data = anvil.server.call('load_invites')
    self.invites = [Invite(invite_data) for invite_data in invites_data]

   
@anvil.server.portable_class
class Invite(h.AttributeToKey):
  def __init__(self, invite_id="", inviter=None, rel_to_inviter="", inviter_guess="", link_key="", 
               response_id="", invitee=None, rel_to_invitee="", invitee_guess=""):
    self.invite_id = invite_id
    self.inviter = inviter
    self.rel_to_inviter = rel_to_inviter
    self.inviter_guess = inviter_guess
    self.link_key = link_key
    self.response_id = response_id
    self.invitee = invitee
    self.rel_to_invitee = rel_to_invitee
    self.invitee_guess = invitee_guess
 
  def update(self, new_self):
    for key, value in vars(new_self).items():
      self[key] = value

  def sc_cancel(self):
    errors = []
    if self.invite_id:
      row = app_tables.invites.get_by_id(self.invite_id)
      if row:
        row.delete()
      else:
        errors.append(f"Invites row not found with id {self.invite_id}")
    for key, value in vars(self).items():
      if key in ['inviter', 'invitee']:
        self[key] = None
      else:
        self[key] = ""
    return self, errors
    
  @property
  def url(self):
    return f"{p.URL}#?invite={self.link_key}"    
  
  @property
  def not_yet_added(self):
    return not self.invite_id and not (self.response_id or self.invitee_guess or self.rel_to_invitee)
      
  @property                   
  def ready_to_add(self):
    return self.inviter_guess and self.rel_to_inviter
  
  @property                   
  def response_ready(self):
    return self.invitee_guess and self.rel_to_invitee 
  
  def relay(self, sc_method=None, kwargs=None):
    if not sc_method:
      sc_method = "serve"
    if not kwargs:
      kwargs = {}
    new_object, errors = anvil.server.call('serve', self, sc_method, kwargs)
    self.update(new_object)
    return errors

  def s_invite_row(self):
    return self._s_row(origin=True)
  
  def s_response_row(self):
    return self._s_row(origin=False)
 
  def _s_row(self, origin):
    row_id = self.invite_id if origin else self.response_id
    if row_id:
      return app_tables.invites.get_by_id(row_id)
    elif self.link_key:
      return app_tables.invites.get(origin=origin, link_key=self.link_key)
    elif self.inviter and self.invitee:
      port_user1 = self.inviter if origin else self.invitee
      port_user2 = self.invitee if origin else self.inviter
      return app_tables.invites.get(origin=origin, user1=port_user1.s_user, user2=port_user2.s_user)
    else:
      print("Warning: not enough information to retrieve invites row.")
      return None

  def _s_sync_user(self, attr_port_user_name, row, column_name, check_auth=False, load_only=False):
    import server_misc as sm
    attr_port_user = getattr(self, attr_port_user_name)
    if check_auth:
      user_to_check = attr_port_user.s_user if attr_port_user else row[column_name]
      if user_to_check:
        sm.get_user(user_to_check.get_id(), require_auth=True)
    if attr_port_user and not load_only:
      row[column_name] = attr_port_user.s_user
    elif row[column_name]:
      setattr(self, attr_port_user_name, sm.get_port_user(row[column_name]))
 
  def _s_sync(self, attr_name, row, column_name, date_updated_column_name="", load_only=False):
    import server_misc as sm
    attr = getattr(self, attr_name)
    if attr and not load_only:
      if row[column_name] != attr:
        row[column_name] = attr
        if date_updated_column_name:
          row[date_updated_column_name] = sm.now()
    elif row[column_name]:
      setattr(self, attr_name, row[column_name])
      
  def _s_sync_invite(self, invite_row, check_auth=True, load_only=False):
    """Returns list of error strings
    
    Assumes invite_row exists (is not None)"""
    if load_only:
      check_auth = False
    errors = []
    self.invite_id = invite_row.get_id()
    self._s_sync_user('inviter', invite_row, 'user1', load_only=load_only, check_auth=check_auth)
    self._s_sync_user('invitee', invite_row, 'user2', load_only=load_only)
    self._s_sync('inviter_guess', invite_row, 'guess', load_only=load_only)
    self._s_sync('rel_to_inviter', invite_row, 'relationship2to1', load_only=load_only, date_updated_column_name='date_described')
    self._s_sync('link_key', invite_row, 'link_key', load_only=load_only)
    return errors
 
  def _s_sync_response(self, response_row, check_auth=True, load_only=False):
    """Returns list of error strings
    
    Assumes response_row exists (is not None)"""
    if load_only:
      check_auth = False
    errors = []
    self.response_id = response_row.get_id()
    self._s_sync_user('invitee', response_row, 'user1', load_only=load_only, check_auth=check_auth)
    self._s_sync_user('inviter', response_row, 'user2', load_only=load_only)
    self._s_sync('invitee_guess', response_row, 'guess', load_only=load_only)
    self._s_sync('rel_to_invitee', response_row, 'relationship2to1', load_only=load_only, date_updated_column_name='date_described')
    self._s_sync('link_key', invite_row, 'link_key', load_only=load_only)
    return errors
    
  def _s_add_response(self):
    """Returns list of error strings"""
    raise(NotImplemented)

  def _s_try_adding_invitee(self, user, invite_row):
    """Returns list of error strings
    
    Assumes invite_row exists (is not None)"""
    errors = []
    import server_misc as sm
    self.invitee = sm.get_port_user(user, distance=0)
    import connections as c
    if user['phone'] and not c.phone_match(self.inviter_guess, user):
      errors.append("The inviter did not accurately provide the last 4 digits of your phone number.")
      sm.add_invite_guess_fail_prompt(self)
      new_self, cancel_errors = self.sc_cancel()
      errors += cancel_errors
    else:
      if invite_row['user2'] and invite_row['user2'] != user:
        print("Warning: invite['user2'] being overwritten")
      invite_row['user2'] = user
    return errors
    
  def sc_serve(self):
    errors = []
    invite_row = self.s_invite_row()
    if invite_row:
      errors += self._s_sync_invite(invite_row)
      response_row = self.s_response_row()
      if response_row:
        errors += self._s_sync_response(response_row)
      elif not self.response_id and self.response_ready:
        errors += self._s_add_response()
      elif self.response_id:
        errors.append("Response row not found")
    elif self.not_yet_added and self.ready_to_add:
      new_self, add_errors = self.sc_add(self.inviter.user_id if self.inviter else "")
      self.update(new_self)
      errors += add_errors
    else:
      errors += "No matching invite found."
    return self, errors

  def sc_add(self, user_id=""):
    """Side effect: Add invites row"""
    import server_misc as sm
    user = sm.get_user(user_id)
    self.inviter = sm.get_port_user(user, distance=0)
    now = sm.now()
    self.link_key = sm.random_code(num_chars=7)
    new_row = app_tables.invites.add_row(date=now,
                                         origin=True,
                                         date_described=now,
                                         distance=1,
                                        )
    errors = self._s_sync_invite(new_row)
    return self, errors
  
  def sc_visit(self, user):
    """Assumes only self.link_key known
    
       Side effects: set invite['user2'] if visitor is logged in,
       likewise for invite_reply['user1'] if it exists"""
    errors = []
    import server_misc as sm
    invite_row = self.s_invite_row()
    if invite_row:
      errors += self._s_sync_invite(invite_row, load_only=True)
      if user:
        errors += self._s_try_adding_invitee(user, invite_row)
      response_row = app_tables.invites.get(origin=False, link_key=self.link_key)
      if response_row:
        errors += self._s_sync_response(response_row, load_only=True)
    else:
      errors.append("Invalid invite link")
    return self, errors

  @staticmethod
  def from_invited(self, inviter_id, user_id=""):
    pass
  