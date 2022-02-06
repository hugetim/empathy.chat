from ._anvil_designer import NameTemplate
from anvil import *
import anvil.users
import anvil.server
from .. import helper as h
from .. import parameters as p


class Name(NameTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.star_button.tooltip = p.STAR_TOOLTIP
    distance = self.item.get('distance')
    if distance and distance < port.UNLINKED:
      self.degree_label.text = h.add_num_suffix(distance)
      self.degree_label.visible = True
    
  def link_1_click(self, **event_args):
    """This method is called when the link is clicked"""
    get_open_form().go_profile(self.item['user_id'])

  def star_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.item.toggle_starred()
    self.refresh_data_bindings()


