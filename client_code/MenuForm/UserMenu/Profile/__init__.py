from ._anvil_designer import ProfileTemplate
from anvil import *
import anvil.server
import anvil.users
from .NameEdit import NameEdit


class Profile(ProfileTemplate):
  state_keys = {'me', 'first', 'last', 'seeking', 'how_empathy', 'profile'}
  
  def __init__(self, user_id="", **properties):
    # Set Form properties and Data Bindings.
    item = anvil.server.call('init_profile', user_id)
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    if self.item['me']:
      name_item = {'first': self.item['first'],
                   'last': self.item['last'],
                   'edits': False,
                  }
      self.column_panel_top.add(NameEdit(name_item))