from ._anvil_designer import NameTemplate
from anvil import *


class Name(NameTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    
  def form_show(self, **event_args):
    """This method is called when the column panel is shown on the screen"""
    print("Name", self.item)

  def link_1_click(self, **event_args):
    """This method is called when the link is clicked"""
    get_open_form().go_profile(self.item['user_id'])

