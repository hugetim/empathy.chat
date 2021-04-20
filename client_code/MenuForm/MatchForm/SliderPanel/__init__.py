from ._anvil_designer import SliderPanelTemplate
from anvil import *
import anvil.server
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users

class SliderPanel(SliderPanelTemplate):
  def __init__(self, **properties):
    """self.item assumed to have these keys: 'visible'"""
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.

  def hide_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.item['visible'] = 0

