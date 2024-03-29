import anvil.server
from . import helper as h
from . import parameters as p

  
@anvil.server.portable_class
class Invite(h.PortItem, h.AttributeToKey):
  no_auth_methods = ['visit', 'register', 'respond']
  repr_desc = "invites.Invite: "
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
    self.connection_successful = False

  def __str__(self):
    return f"my {self.rel_to_inviter} ({self.link_key})"
  
  @property
  def url(self):
    return f"{p.URL}#?invite={self.link_key}"
  
  @property
  def not_yet_added(self):
    return not self.invite_id and not (self.response_id or self.invitee_guess or self.rel_to_invitee)
      
  @property                   
  def ready_to_add(self):
    return not self.invalid_invite()
  
  def invalid_invite(self):
    return Invite._check_guess_rel(self.inviter_guess, self.rel_to_inviter)
  
  def invalid_response(self):
    return Invite._check_guess_rel(self.invitee_guess, self.rel_to_invitee)

  @property
  def from_invite_link(self):
    return bool(self.link_key)
  
  @staticmethod
  def _check_guess_rel(guess, rel):
    validation_errors = []
    if not guess or len(guess) != 4:
      validation_errors.append("Wrong number of digits entered.")
    if not rel or len(rel) < p.MIN_RELATIONSHIP_LENGTH:
      validation_errors.append("Please add a description of your relationship.")
    return validation_errors
  
  @property                   
  def response_ready(self):
    return not self.invalid_response()

  def rel_item(self, for_response):
    if for_response:
      name = self.inviter.name if self.inviter else ""
    else:
      name = self.invitee.name if self.invitee else ""
    return dict(relationship=self.rel_to_invitee if for_response else self.rel_to_inviter,
                phone_last4=self.invitee_guess if for_response else self.inviter_guess,
                name=name,
               )

  def update_from_rel_item(self, item, for_response):
    if for_response:
      self.rel_to_invitee = item['relationship'] #RelationshipOnly
    else:
      self.rel_to_inviter = item['relationship']
      self.inviter_guess = item['phone_last4']
      
  def relay(self, method, kwargs=None):
    if not kwargs:
      kwargs = {}
    if method in self.no_auth_methods:
      new_object = anvil.server.call('serve_invite_unauth', self, method, kwargs)
    else:
      new_object = anvil.server.call('serve_invite', self, method, kwargs)
    self.update(new_object)

