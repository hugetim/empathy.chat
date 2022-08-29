from ._anvil_designer import InviteATemplate
from anvil import *
from ..InviteB import InviteB
from .RelationshipPrompt import RelationshipPrompt
from anvil_extras.utils import wait_for_writeback

class InviteA(InviteATemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    
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
      validation_errors = self.item.invalid_invite()
      if validation_errors:
        self.error("\n".join(validation_errors))
      else:
        errors = self.item.relay('add')
        if errors:
          self.error("\n".join(errors))
        elif self.item.invitee: #existing user
          message = f"You will be linked once {self.item.invitee.name} confirms."
          self.parent.raise_event("x-close-alert", value="success")
          alert(message)
        else:
          parent = self.parent
          self.remove_from_parent()
          parent.add_component(InviteB(item=self.item))
    
  def error(self, text):
    self.error_label.text = text
    self.error_label.visible = True
    

