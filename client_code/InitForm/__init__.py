from ._anvil_designer import InitFormTemplate
from anvil import *
import anvil.server
from .. import rosenberg
from datetime import date


class InitForm(InitFormTemplate):
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.quote_label.text = rosenberg.quote_of_the_day(date.today())
    
  def form_show(self, **event_args):
    """This method is called when the HTML panel is shown on the screen"""
    init_state = anvil.server.call('init')
    open_form('MenuForm', item=init_state)

