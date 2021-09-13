from ._anvil_designer import ConnectionsTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users

class Connections(ConnectionsTemplate):
  item_keys = {'user_id'}
  
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.update()
    
  def update(self):
    self.repeating_panel_1.items = (
      anvil.server.call('get_connections', self.item['user_id'])
    )
    self.refresh_data_bindings()