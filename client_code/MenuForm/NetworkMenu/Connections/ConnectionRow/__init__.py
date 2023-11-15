from ._anvil_designer import ConnectionRowTemplate
from anvil import *
from ..... import helper as h
from ..... import ui_procedures as ui
from ..... import prompts
from ..... import glob
from ..... import invited_procedures as invited
from ..... import portable as port


class ConnectionRow(ConnectionRowTemplate):
  """item attribute is a port.UserFull"""
  
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.trust_level = glob.trust_level
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.degree_label.text = self.item.distance_str_or_groups
    self.last_active_label.text = self.item.last_active_str

  def unconnect_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if ui.disconnect_flow(self.item['user_id'], self.item['name']):
      self.parent.raise_event('x-reset')

  def connect_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if prompts.invite_dialog(port.User(name=self.item['name'], user_id=self.item['user_id']),
                             title="Make a close connection",):
      self.parent.raise_event('x-reset')

  def confirm_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if invited.invited_dialog(port.User(name=self.item['name'], user_id=self.item['user_id'])):
      self.parent.raise_event('x-reset')

  def unread_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    get_open_form().go_profile(self.item['user_id'], tab='history')



