from ._anvil_designer import InviteBTemplate
from anvil import *
import anvil.server
from anvil_extras.utils import wait_for_writeback


class InviteB(InviteBTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.

  def ok_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.parent.raise_event("x-close-alert", value=True)  
    
  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    anvil.server.call('cancel_invite', self.item['link_key'])
    self.parent.raise_event("x-close-alert", value=False)

  def back_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    anvil.server.call('cancel_invite', self.item['link_key'])
    parent = self.parent
    self.remove_from_parent()
    from ..InviteA import InviteA
    parent.add_component(InviteA(item=self.item))
