from ._anvil_designer import Invited2Template
from anvil import *
from ....MenuForm.SettingsForm.Phone import Phone
from ....glob import publisher


class Invited2(Invited2Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    
  def ok_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    publisher.publish("invited", "success")

  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.item.relay('cancel_response')
    publisher.publish("invited", "failure")

  def back_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.item.relay('cancel_response')
    publisher.publish("invited", "go_invited1", self.item)
