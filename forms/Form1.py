from anvil import *
import anvil.server
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.users

class Form1(Form1Template):
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    while not anvil.users.login_with_form():
      pass

  def request_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    anvil.server.call('add_request',anvil.users.get_user().get_id())
    self.status.text = "Status: Requesting empathy. Awaiting an offer..."
      

  def timer_1_tick(self, **event_args):
    """This method is called Every [interval] seconds"""
    pass






