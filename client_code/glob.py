import anvil.facebook.auth
import anvil.users
import anvil.server
from . import parameters as p


trust_level = 0
name = ""


class AttributeToKey:
  def __getitem__(self, key):
    return self.__getattr__(key)

  def __setitem__(self, key, item):
    self.__setattr__(key, item)


class ItemWrapped(AttributeToKey):
  def __init__(self, item):
    self.item = item
 
  def to_data(self):
    return self.item

  def __getattr__(self, key):
    return self.item[key]
  
  def get(self, key, default=None):
    return self.item.get(key, default)
  
#   def __setattr__(self, key, value):
#     self.item[key] = value

    
class Invites(AttributeToKey):
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

    
class Invite(ItemWrapped):
  @property
  def url(self):
    return f"{p.URL}#?invite={self.link_key}"     
        
    
invites = Invites()
