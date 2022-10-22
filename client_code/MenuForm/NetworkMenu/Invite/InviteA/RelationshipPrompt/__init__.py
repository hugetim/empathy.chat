from ._anvil_designer import RelationshipPromptTemplate
from anvil import *


class RelationshipPrompt(RelationshipPromptTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.

  def form_show(self, **event_args):
    """This method is called when the column panel is shown on the screen"""
    name = self.item.get('name')
    if name:
      self.label_1.text = (   
        f"Imagine {name} were about to exchange empathy with another phone buddy "
        f"at an NVC meetup.\nWho would you introduce {name} as?"
      )
      self.label_4.text = (
        f"Please provide the last 4 digits of {name}'s phone number "
        "to confirm you are phone buddies:"
      )
  
  def relationship_text_box_pressed_enter(self, **event_args):
    """This method is called when the user presses Enter in this text box"""
    self.phone_last4_text_box.focus()
  
  def phone_last4_text_box_pressed_enter(self, **event_args):
    """This method is called when the user presses Enter in this text box"""
    self.raise_event('x-continue')

