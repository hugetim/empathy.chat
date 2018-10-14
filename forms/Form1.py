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
    jitsi_code = anvil.server.call('add_request',anvil.users.get_user().get_id())
    if jitsi_code == None:
      self.status.text = "Status: Requesting empathy. Awaiting an offer..."
    else:
      self.status.text = "Use Jitsi " + jitsi_code
    self.request_button.visible = False
    self.offer_button.visible = False

  def offer_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    jitsi_code = anvil.server.call('add_offer',anvil.users.get_user().get_id())
    if jitsi_code == None:
      self.status.text = "Status: Offering empathy. Awaiting a request..."
    else:
      self.status.text = "Use Jitsi " + jitsi_code
    self.request_button.visible = False
    self.offer_button.visible = False
    

  def timer_1_tick(self, **event_args):
    """This method is called Every [interval] seconds"""
    pass






