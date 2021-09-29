from ._anvil_designer import InviteATemplate
from anvil import *
import anvil.server
from anvil_extras.utils import wait_for_writeback
from ..InviteB import InviteB

class InviteA(InviteATemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.

  def relationship_text_box_pressed_enter(self, **event_args):
    """This method is called when the user presses Enter in this text box"""
    self.phone_last4_text_box.focus()

  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.parent.raise_event("x-close-alert", value=False)

  def phone_last4_text_box_pressed_enter(self, **event_args):
    """This method is called when the user presses Enter in this text box"""
    if self.continue_button.enabled:
      self.continue_button_click()

  @wait_for_writeback    
  def continue_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if len(self.item['phone_last4']) != 4:
      self.error("Wrong number of digits entered.")
    elif len(self.item['relationship']) < 3:
      self.error("Please add a description of your relationship.")
    else:
      invite_item = anvil.server.call('add_invite', self.item)
      parent = self.parent
      self.remove_from_parent()
      self.item.update(invite_item)
      parent.add_component(InviteB(item=self.item))
    
  def error(self, text):
    self.error_label.text = text
    self.error_label.visible = True
    




