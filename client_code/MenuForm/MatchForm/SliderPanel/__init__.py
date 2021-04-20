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
    self.item['visible'] = False
    self.refresh_data_bindings()

  def submit_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.item['status'] = "submitted"
    self.refresh_data_bindings()
    their_value = anvil.server.call('submit_slider', 
                                    self.my_slider.value)
    if their_value:
      self.receive_value(their_value)

  def receive_value(self, their_value):
    self.item['their_value'] = their_value
    self.item['visible'] = True
    self.item['status'] = "received"
    self.refresh_data_bindings()
      
  def show_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.item['visible'] = True
    self.refresh_data_bindings()

