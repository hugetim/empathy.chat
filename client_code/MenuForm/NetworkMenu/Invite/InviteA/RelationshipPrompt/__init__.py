from ._anvil_designer import RelationshipPromptTemplate
from anvil import *
import anvil.server
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users

class RelationshipPrompt(RelationshipPromptTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.

  def relationship_text_box_pressed_enter(self, **event_args):
    """This method is called when the user presses Enter in this text box"""
    self.phone_last4_text_box.focus()
  
  def phone_last4_text_box_pressed_enter(self, **event_args):
    """This method is called when the user presses Enter in this text box"""
    if self.continue_button.enabled:
      self.continue_button_click()
