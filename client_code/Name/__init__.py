from ._anvil_designer import NameTemplate
from anvil import *
import anvil.facebook.auth
import anvil.users
import anvil.server
from .. import helper as h

class Name(NameTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    distance = self.item.get('distance')
    if distance:
      self.degree_label.text = h.add_num_suffix(distance)
      self.degree_label.visible = True
    
  def link_1_click(self, **event_args):
    """This method is called when the link is clicked"""
    get_open_form().go_profile(self.item['user_id'])

