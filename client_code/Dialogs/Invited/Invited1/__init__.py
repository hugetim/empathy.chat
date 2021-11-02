from ._anvil_designer import Invited1Template
from anvil import *
import anvil.server
from ..Invited2 import Invited2
from ....MenuForm.NetworkMenu.Invite.InviteA.RelationshipPrompt import RelationshipPrompt


class Invited1(Invited1Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.

  def form_show(self, **event_args):
    """This method is called when the column panel is shown on the screen"""
    self.relationship_prompt = RelationshipPrompt(
      item={k: self.item[k] for k in {'relationship', 'phone_last4'}}
    )
    self.linear_panel_1.add_component(self.relationship_prompt)
    self.relationship_prompt.label_4.text = (
      "Please also provide the last 4 digits of a phone number "
      f"at which {self.item['inviter']} can receive text messages "
      "to verify your close connection:"
    )
    
  def continue_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.item.update(self.relationship_prompt.item)
    if len(self.item['phone_last4']) != 4:
      self.error("Wrong number of digits entered.")
    elif len(self.item['relationship']) < 3:
      self.error("Please add a description of your relationship.")
    else:
      invited_item = anvil.server.call('add_invited', self.item)
      if invited_item:
        parent = self.parent
        self.remove_from_parent()
        self.item.update(invited_item)
        parent.add_component(Invited2(item=self.item))
      else:
        self.error(f"The last 4 digits you provided do not match {self.item['inviter']}'s phone number.")

  def error(self, text):
    self.error_label.text = text
    self.error_label.visible = True
    

