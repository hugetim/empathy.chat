from ._anvil_designer import ConnectionRowTemplate
from anvil import *
import anvil.users
import anvil.server
from ..... import helper as h
from ..... import ui_procedures as ui
from ..... import prompts
from ..... import glob
from ..... import invited
from ..... import portable as port


class ConnectionRow(ConnectionRowTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.trust_level = glob.trust_level
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.degree_label.text = h.add_num_suffix(self.item['distance'])
    self.last_active_label.text = h.short_date_str(h.as_local_tz(self.item['last_active']))
    if self.item['status'] == "invite":
      self.degree_label.text += " (pending invite)"

  def unconnect_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if ui.disconnect_flow(self.item['user_id'], self.item['name']):
      self.parent.raise_event('x-reset')

  def connect_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if prompts.invite_dialog(port.User(name=self.item['name'], user_id=self.item['user_id'])):
      self.parent.raise_event('x-reset')

  def confirm_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if invited.invited_dialog(port.User(name=self.item['name'], user_id=self.item['user_id'])):
      self.parent.raise_event('x-reset')


