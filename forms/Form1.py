from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.server
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.users
import datetime

class Form1(Form1Template):
  current_status = None
  user = None
  match_start = None
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    
    while not anvil.users.login_with_form():
      pass
    self.user = anvil.users.get_user()
    self.current_status = anvil.server.call('get_status',self.user.get_id())
    self.set_form_status(self.current_status)
    # initialize new users
    if anvil.server.call('get_trust_level',self.user.get_id()) == None:
      self.user.update(trust_level=0) 

  def request_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    jitsi_code = anvil.server.call('add_request',self.user.get_id())
    if jitsi_code == None:
      self.status.text = "Status: Requesting empathy. Awaiting an offer..."
      self.set_form_status("requesting")
    else:
      self.status.text = "Use Jitsi " + jitsi_code
      self.set_form_status("matched")

  def offer_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    jitsi_code = anvil.server.call('add_offer',self.user.get_id())
    if jitsi_code == None:
      self.status.text = "Status: Offering empathy. Awaiting a request..."
      self.set_form_status("offering")
    else:
      self.status.text = "Use Jitsi " + jitsi_code
      self.set_form_status("matched")
    

  def timer_1_tick(self, **event_args):
    """This method is called Every 5 seconds"""
    if self.current_status in ["requesting", "offering"]:
      new_status = anvil.server.call('get_status',self.user.get_id())
      if new_status == "matched":
        ready = confirm("A match is available. Are you ready?")
        if ready:
          self.current_status = new_status
        else:
          self.current_status = None
          anvil.server.call('cancel',self.user.get_id())
        self.set_form_status(self.current_status)
    elif self.current_status == "matched":
      new_status = anvil.server.call('get_status',self.user.get_id())
      timer = datetime.datetime.now() - self.match_start
      print timer.seconds
      if new_status=="matched" and timer.seconds > 10:
        new_status = "empathy"
      if new_status != "matched":
        self.current_status = new_status
        self.set_form_status(self.current_status)
      
  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.current_status = None
    anvil.server.call('cancel',self.user.get_id())
    self.set_form_status(self.current_status)

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
       jitsi_code = anvil.server.call('get_code',self.user.get_id())
       self.status.text = "Use Jitsi " + jitsi_code
       self.match_start = datetime.datetime.now()
       self.complete_button.visible=False
       self.cancel_button.visible = True
       self.request_button.visible = False
       self.offer_button.visible = False
     elif user_status == "empathy":
       self.complete_button.visible = True
       self.cancel_button.visible = False
       self.request_button.visible = False
       self.offer_button.visible = False
     else:
       self.status.text = "Choose an option:"
       self.complete_button.visible=False
       self.cancel_button.visible = False
       self.request_button.visible = True
       self.offer_button.visible = True

  def complete_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.current_status = None
    self.set_form_status(self.current_status)


  



