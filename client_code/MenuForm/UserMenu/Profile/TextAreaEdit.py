from ._anvil_designer import TextAreaEditTemplate
from anvil import *
import anvil.users
import anvil.server


class TextAreaEdit(TextAreaEditTemplate):
  item_keys = {'prompt', 'text'}
  
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.

  def text_area_change(self, **event_args):
    """This method is called when the text in this text box is edited"""
    if not self.save_button.enabled:
      self.save_button.enabled = True

  def save_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.raise_event("x-close-alert", value=True)

  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.raise_event("x-close-alert", value=False)
    







