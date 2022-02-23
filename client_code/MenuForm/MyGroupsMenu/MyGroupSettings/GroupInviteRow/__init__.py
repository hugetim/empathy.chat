from ._anvil_designer import GroupInviteRowTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ..... import ui_procedures as ui


class GroupInviteRow(GroupInviteRowTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.link.url = self.item.url
    self.link.text = self.item.link_key

  def copy_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    ui.copy_to_clipboard(self.link.url, desc="The invite link")
