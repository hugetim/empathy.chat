from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
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
    user = anvil.users.get_user()
    user_status = anvil.server.call('get_status',user.get_id())
    self.set_form_status(user_status)
    # initialize new users
    if anvil.server.call('get_trust_level',user.get_id()) == None:
      user.update(trust_level=0) 

  def request_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    jitsi_code = anvil.server.call('add_request',anvil.users.get_user().get_id())
    if jitsi_code == None:
      self.status.text = "Status: Requesting empathy. Awaiting an offer..."
      self.set_form_status("requesting")
    else:
      self.status.text = "Use Jitsi " + jitsi_code
      self.set_form_status("matched")

  def offer_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    jitsi_code = anvil.server.call('add_offer',anvil.users.get_user().get_id())
    if jitsi_code == None:
      self.status.text = "Status: Offering empathy. Awaiting a request..."
      self.set_form_status("offering")
    else:
      self.status.text = "Use Jitsi " + jitsi_code
      self.set_form_status("matched")
    

  def timer_1_tick(self, **event_args):
    """This method is called Every [interval] seconds"""
    pass


  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    pass

  def set_form_status(self, user_status):
     if user_status == "requesting":
       self.status.text = "Status: Requesting empathy. Awaiting an offer..."
       self.cancel_button.visible = True
       self.request_button.visible = False
       self.offer_button.visible = False
     elif user_status == "offering":
       self.status.text = "Status: Offering empathy. Awaiting a request..."
       self.cancel_button.visible = True
       self.request_button.visible = False
       self.offer_button.visible = False
     elif user_status == "matched":
       code = anvil.server.call('get_code',anvil.users.get_user().get_id())
       self.status.text = "Use Jitsi " + jitsi_code
       self.complete_button.visible=True
       self.cancel_button.visible = True
       self.request_button.visible = False
       self.offer_button.visible = False
     else:
       self.status.text = "Choose an option:"
       self.complete_button.visible=False
       self.cancel_button.visible = False
       self.request_button.visible = True
       self.offer_button.visible = True





