from ._anvil_designer import UserMenuTemplate
from anvil import *
import anvil.server
import anvil.users
from .Profile import Profile
from ..ConnectionsMenu.Connections import Connections
from .History import History
from ... import parameters as p

class UserMenu(UserMenuTemplate):
  item_keys = {'user_id', 'tab'}
  
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
   
    # Any code you write here will run when the form opens.
    self.connections_tab_button.visible = (
      self.item['user_id']
      and self.item['user_id'] != anvil.users.get_user().get_id()
    )
    self.top_form = get_open_form()
    init_content_selector = {'profile': self.go_profile,
                     'connections': self.go_connections,
                     'history': self.go_history,
                    }
    init_content_selector[self.item['tab']]()
    
  def clear_page(self):
    for button in self.tabs_flow_panel.get_components():
      button.background = p.NONSELECTED_TAB_COLOR
    self.content_column_panel.clear()
      
  def load_component(self, content):
    """Reset MenuForm and load content form"""
    self.clear_page()
    self.content = content
    self.content_column_panel.add_component(self.content)  

  def go_profile(self):
    content = Profile()
    self.load_component(content)
    self.profile_tab_button.background = p.SELECTED_TAB_COLOR    
    
  def go_connections(self):
    assert self.item['user_id'] != anvil.users.get_user().get_id()
    content = Connections(item={'user_id': self.item['user_id']})
    self.load_component(content)
    self.connections_tab_button.background = p.SELECTED_TAB_COLOR

  def go_history(self):
    content = History()
    self.load_component(content)
    self.history_tab_button.background = p.SELECTED_TAB_COLOR
    
  def profile_tab_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.go_profile()
    
  def connections_tab_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.go_connections()

  def history_tab_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.go_history()

