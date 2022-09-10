from ._anvil_designer import InviteBTemplate
from anvil import *
from ..... import ui_procedures as ui


class InviteB(InviteBTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.

  def ok_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.parent.go_invite_e(self.item)
    
  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.item.relay('cancel')
    self.parent.raise_event("x-close-alert", value=False)

  def back_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.item.relay('cancel')
    self.parent.go_invite_a(self.item)

  def copy_button_click(self, **event_args):
    ui.copy_to_clipboard(self.link_1.url, desc="The invite link")
