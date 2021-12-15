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
  
  def relay(self, sc_method=None, kwargs=None):
    if not sc_method:
      sc_method = "serve"
    if not kwargs:
      kwargs = {}
    new_object, errors = anvil.server.call('serve', self, sc_method, kwargs)
    self.update(new_object)
    return errors

  def sc_serve(self):
    pass
  
  def sc_add(self, user_id=""):
    """Side effect: Add invites row"""
    import server_misc as sm
    user = sm.get_user(user_id)
    self.inviter = sm.get_port_user(user, distance=0)
    now = sm.now()
    self.link_key = sm.random_code(num_chars=7)
    new_row = app_tables.invites.add_row(date=now,
                                         origin=True,
                                         user1=self.inviter.s_user,
                                         relationship2to1=self.rel_to_inviter,
                                         date_described=now,
                                         guess=self.inviter_guess,
                                         distance=1,
                                         link_key=self.link_key,
                                        )
    self.invite_id = new_row.get_id()
    return self, []
  
  def sc_visit(self, user):
    """Assumes only self.link_key known
    
       Side effects: set invite['user2'] if visitor is logged in,
       likewise for invite_reply['user1'] if it exists"""
    errors = []
    import server_misc as sm
    if not self.invite_id:
      invite = app_tables.invites.get(origin=True, link_key=self.link_key)
      self.invite_id = invite.get_id()
    else:
      invite = app_tables.invites.get_by_id(self.invite_id)
    if invite:
      self.rel_to_inviter = invite['relationship2to1']
      self.inviter_guess = invite['guess']
      self.inviter = sm.get_port_user(invite['user1'], distance=99)
      if user:
        self.invitee = sm.get_port_user(user, distance=0)
        import connections as c
        if user['phone'] and not c.phone_match(self.inviter_guess, user):
          errors.append("The inviter did not accurately provide the last 4 digits of your phone number.")
          sm.add_invite_guess_fail_prompt(self)
          new_self, cancel_errors = self.sc_cancel()
          return new_self, errors + cancel_errors
        else:
          invite['user2'] = user
          if invite['user2'] and invite['user2'] != user:
            print("Warning: invite['user2'] being overwritten")
      invite_reply = app_tables.invites.get(origin=False, link_key=self.link_key)
      if invite_reply:
        self.rel_to_invitee = invite_reply['relationship2to1']
        self.invitee_guess = invite_reply['guess']
        invite_reply['user1'] = user
    else:
      errors.append("Invalid invite link")
    return self, errors

  @staticmethod
  def from_invited(self, inviter_id, user_id=""):
    pass
  