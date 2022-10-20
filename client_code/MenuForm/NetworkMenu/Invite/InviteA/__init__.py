from ._anvil_designer import InviteATemplate
from anvil import *
from .RelationshipPrompt import RelationshipPrompt
from ..... import invite_controller
from .....glob import publisher
from anvil_extras.utils import wait_for_writeback


class InviteA(InviteATemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    publisher.subscribe("invite_a_error", self, self.dispatch_handler)
    
  def form_show(self, **event_args):
    """This method is called when the column panel is shown on the screen"""
    self.relationship_prompt = RelationshipPrompt(item=self.item.rel_item(for_response=False))
    self.linear_panel_1.add_component(self.relationship_prompt)
    self.relationship_prompt.add_event_handler('x-continue', self.continue_button_click)

  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.parent.raise_event("x-close-alert", value=False)
  
  @wait_for_writeback
  def continue_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if self.continue_button.enabled:
      self.item.update_from_rel_item(self.relationship_prompt.item, for_response=False)
      invite_controller.submit_invite(self.item)
    
  def error(self, text):
    self.error_label.text = text
    self.error_label.visible = True
    
  def dispatch_handler(self, dispatch):
    self.error(dispatch.title)
