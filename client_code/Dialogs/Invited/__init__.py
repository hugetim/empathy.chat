from ._anvil_designer import InvitedTemplate
from anvil import *
import anvil.facebook.auth
import anvil.users
import anvil.server
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class Invited(InvitedTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self._content = self.spacer_1
    self.go_invited1(self.item)

  def _reset_and_load(self, component):
    self._content.remove_from_parent()
    self._content = component
    self.add_component(self._content)
    
  def go_invited2(self, item):
    from .Invited2 import Invited2
    self._reset_and_load(Invited2(item=item))
    
  def go_invited1(self, item):
    from .Invited1 import Invited1
    self._reset_and_load(Invited1(item=item))

