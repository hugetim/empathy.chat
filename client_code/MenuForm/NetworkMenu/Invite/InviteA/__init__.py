from ._anvil_designer import InviteATemplate
from anvil import *
import anvil.server
from ..InviteB import InviteB
from .RelationshipPrompt import RelationshipPrompt

class InviteA(InviteATemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
  def form_show(self, **event_args):
    """This method is called when the column panel is shown on the screen"""
    self.relationship_prompt = RelationshipPrompt(item={k:self.item[k] for k in {'relationship', 'phone_last4'}})
    self.linear_panel_1.add_component(self.relationship_prompt)

  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.parent.raise_event("x-close-alert", value=False)
  
  def continue_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.item.update(self.relationship_prompt.item)
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
    

