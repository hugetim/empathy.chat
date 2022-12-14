from ._anvil_designer import RelationshipPromptOnlyTemplate
from anvil import *


class RelationshipPromptOnly(RelationshipPromptOnlyTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.

  def form_show(self, **event_args):
    """This method is called when the column panel is shown on the screen"""
    name = self.item.get('name')
    if name:
      self.label_1.text = (   
        f"Who would you introduce {name} as?"
      )

  def relationship_text_box_pressed_enter(self, **event_args):
    """This method is called when the user presses Enter in this text box"""
    self.raise_event('x-continue')
