from ._anvil_designer import NameEditTemplate
from anvil import *
import anvil.users
import anvil.server
from .....relationship import Relationship
from ..... import glob


class NameEdit(NameEditTemplate):
  item_keys = {'first', 'last'}
  
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.first_name_panel.tooltip = "The name by which you'd like to be addressed. Pseudonyms welcome (except for group hosts)."
    self.last_name_panel.tooltip = Relationship.LAST_NAME_NOTE
    
  def form_show(self, **event_args):
    if glob.MOBILE:
      self.note_label.text = f"Note:\nFirst Name - {self.first_name_panel.tooltip}\nLast Name - {self.last_name_panel.tooltip}"
      
  def text_box_change(self, **event_args):
    """This method is called when the text in this text box is edited"""
    self.save_button.enabled = self.first_name_text_box.text

  def save_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if self.save_button.enabled:
      self.raise_event("x-close-alert", value=True)

  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.raise_event("x-close-alert", value=False)
    