from ._anvil_designer import InviteRowTemplate
from anvil import *
import anvil.facebook.auth
import anvil.server
import anvil.users
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .....Name import Name

class InviteRow(InviteRowTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    user2 = self.item.get('user2')
    if user2:
      self.link.visible = False
      name_item = {'name': user2.name, 'confirmed': user2.confirmed, 'user_id': user2.user_id}
      self.name = Name(item=name_item)
      self.name_or_url_flow_panel.add_component(self.name)
    else:
      self.link.url = self.item.url
      self.link.text = "Invite Link"
    print(self.item['guess'])

