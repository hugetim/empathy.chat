from ._anvil_designer import NameEditTemplate
from anvil import *
import anvil.server


class NameEdit(NameEditTemplate):
  state_keys = {'first', 'last', 'edits'}
  
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.

  def update(self):
    self.refresh_data_bindings()
    
  def text_box_change(self, **event_args):
    """This method is called when the text in this text box is edited"""
    if not self.items['edits']:
      self.items['edits'] = True
      self.update()

  def save_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    anvil.server.call('save_name', self.item)
    self.item['edits'] = False
    self.update()
    
  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.item = anvil.server.call('get_name')
    self.update()
    







