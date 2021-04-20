from ._anvil_designer import SliderPanelTemplate
from anvil import *
import anvil.server


class SliderPanel(SliderPanelTemplate):
  def __init__(self, **properties):
    """self.item assumed to have these keys: 
    'visible',
    'their_value', default 5
    'my_value', default 5
    'status' in [None, 'submitted', 'received']
    """
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.

  def hide_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.item['visible'] = 0

  def submit_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.item['status'] = "submitted"
    self.item['status'], self.item['their_value'] = anvil.server.call('submit_slider', 
                                                                      self.my_slider.value)
