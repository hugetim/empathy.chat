from ._anvil_designer import MyGroupMembersRowTemplate
from anvil import *
import anvil.server
from anvil_extras.utils import wait_for_writeback
from ..... import helper as h
from ..... import ui_procedures as ui
from ..... import prompts
from ..... import glob
from ..... import invited
from ..... import portable as port


class MyGroupMembersRow(MyGroupMembersRowTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.trust_level = glob.trust_level
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    if self.item['distance'] < port.UNLINKED:
      self.degree_label.text = self.item.distance_str
    self.last_active_label.text = self.item.last_active_str

  def unconnect_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if ui.disconnect_flow(self.item['user_id'], self.item['name']):
      self.parent.raise_event('x-reset')

  def connect_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if prompts.invite_dialog(port.User(name=self.item['name'], user_id=self.item['user_id']),
                             title="Form a new close link",
                            ):
      self.parent.raise_event('x-reset')

  def confirm_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if invited.invited_dialog(port.User(name=self.item['name'], user_id=self.item['user_id'])):
      self.parent.raise_event('x-reset')

  @wait_for_writeback
  def guest_allowed_check_box_change(self, **event_args):
    """This method is called when this checkbox is checked or unchecked"""
    anvil.server.call('update_guest_allowed', self.item)
    self.refresh_data_bindings()
