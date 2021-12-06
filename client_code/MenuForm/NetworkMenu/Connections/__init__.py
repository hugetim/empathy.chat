from ._anvil_designer import ConnectionsTemplate
from anvil import *
import anvil.facebook.auth
import anvil.users
import anvil.server
from .... import helper as h


class Connections(ConnectionsTemplate):
  item_keys = {'user_id'}
  
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    def event_update(**event_args):
      return self.update()                    
    self.repeating_panel_1.set_event_handler('x-reset', event_update)
    self.update()
    
  def update(self):
    self.repeating_panel_1.items = (
      anvil.server.call('get_connections', self.item['user_id'])
    )
    self.refresh_data_bindings()