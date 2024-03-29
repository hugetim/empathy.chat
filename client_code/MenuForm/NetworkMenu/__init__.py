from ._anvil_designer import NetworkMenuTemplate
from anvil import *
from .Connections import Connections
from .Blocks import Blocks
from .Invites import Invites
from .Groups import Groups
from ... import parameters as p
from ... import glob

class NetworkMenu(NetworkMenuTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
   
    # Any code you write here will run when the form opens.
    self.top_form = get_open_form()
    self.invites_tab_button.visible = glob.trust_level >= 3
    self.groups_tab_button.visible = glob.their_groups
    self.go_connections()
    
  def clear_page(self):
    for button in self.tabs_flow_panel.get_components():
      button.background = p.NONSELECTED_TAB_COLOR
      button.role = ""
    self.content_column_panel.clear()

  def select_tab_button(self, button):
    button.background = p.SELECTED_TAB_COLOR
    button.role = "raised"
  
  def load_component(self, content):
    """Reset MenuForm and load content form"""
    self.clear_page()
    self.content = content
    self.content_column_panel.add_component(self.content)  
    
  def go_connections(self):
    content = Connections(item={'user_id': ""})
    self.load_component(content)
    self.select_tab_button(self.network_tab_button)

  def go_blocks(self):
    content = Blocks()
    self.load_component(content)
    self.select_tab_button(self.blocks_tab_button)
    
  def go_invites(self):
    content = Invites()
    self.load_component(content)
    self.select_tab_button(self.invites_tab_button)

  def go_groups(self):
    content = Groups()
    self.load_component(content)
    self.select_tab_button(self.groups_tab_button)
  
  def network_tab_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.go_connections()

  def blocks_tab_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.go_blocks()

  def invites_tab_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.go_invites()

  def groups_tab_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.go_groups()
