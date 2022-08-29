from ._anvil_designer import Invited2Template
from anvil import *
from ....MenuForm.SettingsForm.Phone import Phone
from .... import invited


class Invited2(Invited2Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    
  def ok_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.parent.raise_event("x-close-alert", value=True)

  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.item.relay('cancel_response')
    self.parent.raise_event("x-close-alert", value=False)

  def back_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.item.relay('cancel_response')
    self.parent.go_invited1(self.item)
