from ._anvil_designer import ConnectionsTemplate
from anvil import *
import anvil.users
from .... import network_controller as nc
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
    items = nc.get_connections(self.item['user_id'])
    items.sort(key=lambda pu: (pu.distance_str_or_groups, h.reverse_compare(pu['last_active'])))
    self.repeating_panel_1.items = items
    has_degrees = any([item.distance_str for item in items])
    has_groups = any([not item.distance_str and item.common_group_names for item in items])
    if not has_degrees or not has_groups:
      columns = list(self.data_grid_1.columns)
      [degree_column] = [column for column in columns if column['data_key'] == "degree"]
      degree_index = columns.index(degree_column)
      columns[degree_index]['title'] = "Degree" if has_degrees else "Group(s)"
      self.data_grid_1.columns = columns
    self.refresh_data_bindings()