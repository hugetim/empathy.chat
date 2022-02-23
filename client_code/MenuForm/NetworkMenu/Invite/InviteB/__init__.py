from ._anvil_designer import InviteBTemplate
from anvil import *
import anvil.users
import anvil.server
from anvil_extras.utils import wait_for_writeback
from ..... import ui_procedures as ui
from ..InviteE import InviteE


class InviteB(InviteBTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.

  def ok_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    parent = self.parent
    self.remove_from_parent()
    parent.add_component(InviteE(item=self.item))
    
  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.item.relay('cancel')
    self.parent.raise_event("x-close-alert", value=False)

  def back_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.item.relay('cancel')
    parent = self.parent
    self.remove_from_parent()
    from ..InviteA import InviteA
    parent.add_component(InviteA(item=self.item))

  def copy_button_click(self, **event_args):
    ui.copy_to_clipboard(self.link_1.url, desc="The invite link")
