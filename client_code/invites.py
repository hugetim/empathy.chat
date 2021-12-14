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

    
class Invite(h.ItemWrapped):
  @property
  def url(self):
    return f"{p.URL}#?invite={self.link_key}"     
        
    