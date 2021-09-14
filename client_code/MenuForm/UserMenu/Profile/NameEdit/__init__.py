from ._anvil_designer import NameEditTemplate
from anvil import *
import anvil.server


class NameEdit(NameEditTemplate):
  item_keys = {'first', 'last'}
  
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.

  def text_box_change(self, **event_args):
    """This method is called when the text in this text box is edited"""
    self.save_button.enabled = self.first_name_text_box.text

  def save_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.raise_event("x-close-alert", value=True)

  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.raise_event("x-close-alert", value=False)
    







