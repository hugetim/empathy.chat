from ._anvil_designer import MyGroupsMenuTemplate
from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users
import anvil.server
from .MyGroupSettings import MyGroupSettings
from .MyGroupMembers import MyGroupMembers
from .MyGroupInvites import MyGroupInvites
from ... import parameters as p
from ... import glob

class MyGroupsMenu(MyGroupsMenuTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    glob.my_groups.relay('load')
    self.reset()

  @property
  def selected_group(self):
    return self.groups_drop_down.selected_value
    
  def reset(self):
    self.update_drop_down()
    if glob.my_groups:
      self.go_group_settings()
    self.groups_drop_down.visible = glob.my_groups
    self.tabs_flow_panel.visible = glob.my_groups
    self.content_column_panel.visible = glob.my_groups

  def update_drop_down(self):
    self.groups_drop_down.items = [(g['name'], g) for g in glob.my_groups]

  def groups_drop_down_change(self, **event_args):
    """This method is called when an item is selected"""
    self.content.group = self.groups_drop_down.selected_value
    self.content.update()
    
  def create_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    glob.my_groups.relay('add')
    self.groups_drop_down.selected_value = glob.my_groups[-1]
    self.reset()
      
  def clear_page(self):
    for button in self.tabs_flow_panel.get_components():
      button.background = p.NONSELECTED_TAB_COLOR
    self.content_column_panel.clear()

  def load_component(self, content):
    """Reset MenuForm and load content form"""
    self.clear_page()
    self.content = content
    self.content_column_panel.add_component(self.content)

  def go_group_settings(self):
    content = MyGroupSettings(menu=self)
    self.load_component(content)
    self.group_settings_tab_button.background = p.SELECTED_TAB_COLOR

  def go_members(self):
    content = MyGroupMembers()
    self.load_component(content)
    self.members_tab_button.background = p.SELECTED_TAB_COLOR

  def go_invites(self):
    content = MyGroupInvites()
    self.load_component(content)
    self.invites_tab_button.background = p.SELECTED_TAB_COLOR  
    
  def group_settings_tab_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.go_group_settings()

  def members_tab_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.go_members()

  def invites_tab_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.go_invites()
