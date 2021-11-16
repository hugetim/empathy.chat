from ._anvil_designer import RelationshipPromptTemplate
from anvil import *
import anvil.server
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

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
        f"Briefly describe your relationship to {name} "
        "and their current experience level with NVC empathy, if you know:"
      )
      self.label_4.text = (
        "Please provide the last 4 digits of the phone number {name} has provided to empathy.chat "
        "to confirm your close connection:"
      )
  
  def relationship_text_box_pressed_enter(self, **event_args):
    """This method is called when the user presses Enter in this text box"""
    self.phone_last4_text_box.focus()
  
  def phone_last4_text_box_pressed_enter(self, **event_args):
    """This method is called when the user presses Enter in this text box"""
    self.raise_event('x-continue')

