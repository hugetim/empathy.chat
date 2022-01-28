from ._anvil_designer import MobileAlertTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class MobileAlert(MobileAlertTemplate):
  def __init__(self, status, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    if status == "requesting":
      self.requesting_label.visible = True
