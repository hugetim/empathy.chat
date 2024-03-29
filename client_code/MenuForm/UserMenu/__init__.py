from ._anvil_designer import UserMenuTemplate
from anvil import *
from .Profile import Profile
from ..NetworkMenu.Connections import Connections
from .History import History
from ... import parameters as p
from ... import helper as h
from ... import glob


class UserMenu(UserMenuTemplate):
  item_keys = {'user_id', 'tab'}
  
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
   
    # Any code you write here will run when the form opens.
    self.connections_tab_button.visible = (
      self.item['user_id']
      and self.item['user_id'] != glob.logged_in_user_id
    )
    self.history_tab_button.visible = self.connections_tab_button.visible ## TEMPORARY
    self.top_form = get_open_form()
    init_content_selector = {'profile': self.go_profile,
                             'connections': self.go_connections,
                             'history': self.go_history,
                            }
    init_content_selector[self.item['tab']]()
    
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

  def go_profile(self):
    self.content = Profile(self.item['user_id'])
    self.load_component(self.content)
    self.select_tab_button(self.profile_tab_button)
    
  def go_connections(self):
    if self.item['user_id'] == glob.logged_in_user_id:
      h.warning(f"UserMenu.go_connections called on current user")
    self.content = Connections(item={'user_id': self.item['user_id']})
    self.load_component(self.content)
    self.select_tab_button(self.connections_tab_button)

  def go_history(self):
    self.content = History(item={'user_id': self.item['user_id']})
    self.load_component(self.content)
    self.select_tab_button(self.history_tab_button)
    
  def profile_tab_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.go_profile()
    
  def connections_tab_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.go_connections()

  def history_tab_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.go_history()

