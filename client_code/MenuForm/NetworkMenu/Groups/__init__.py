from ._anvil_designer import GroupsTemplate
from anvil import *
from .... import glob


class Groups(GroupsTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.repeating_panel_1.set_event_handler('x-reset', self.reset)
    self.update()
    
  def update(self):
    items = glob.their_groups.values()
    #items.sort(key=lambda pu: (pu.distance_str_or_groups, h.reverse_compare(pu['last_active'])))
    self.repeating_panel_1.items = items
    self.refresh_data_bindings()

  def reset(self, **event_args):
    glob.update_lazy_vars()
    self.update()