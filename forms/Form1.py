from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.server
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.users
import datetime

class Form1(Form1Template):
  seconds_to_cancel = 90
  current_status = None
  user_id = None
  match_start = None  
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    
    while not anvil.users.login_with_form():
      pass
    user = anvil.users.get_user()
    self.user_id = user.get_id()
    self.current_status = anvil.server.call('get_status',self.user.get_id())
    if self.current_status == "matched":
      self.match_start = anvil.server.call('get_match_start', 
                                           self.user.get_id())
      if self.match_start == None:
        # matching data table indicates no longer matched
        self.current_status = anvil.server.call('get_status',
                                                self.user.get_id())
      else:
        timer = datetime.datetime.now(self.match_start.tzinfo) - self.match_start
        print timer.seconds
        if timer.seconds > self.seconds_to_cancel:
          ongoing = confirm("Is your empathy session, begun "
                            + str(timer.seconds/60)
                            + " minutes ago, still ongoing?")
          if ongoing:
            self.current_status = "empathy"
          else:
            self.current_status = None
            anvil.server.call('match_complete',self.user.get_id())
    self.set_form_status(self.current_status)
    # initialize new users
    anvil.server.call('get_trust_level',self.user.get_id())

  def request_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    jitsi_code = anvil.server.call('add_request',self.user.get_id())
    if jitsi_code == None:
      self.status.text = "Status: Requesting empathy. Awaiting an offer..."
      self.set_form_status("requesting")
    else:
      self.set_form_status("matched")

  def offer_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    jitsi_code = anvil.server.call('add_offer',self.user.get_id())
    if jitsi_code == None:
      self.status.text = "Status: Offering empathy. Awaiting a request..."
      self.set_form_status("offering")
    else:
      self.match_start = datetime.datetime.utcnow()
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
        self.match_start = datetime.datetime.utcnow()
        self.set_form_status(self.current_status)
    elif self.current_status == "matched":
      new_status = anvil.server.call('get_status',self.user.get_id())
      timer = datetime.datetime.now(self.match_start.tzinfo) - self.match_start
      print timer.seconds
      if new_status=="matched" and timer.seconds > self.seconds_to_cancel:
        new_status = "empathy"
      if new_status != "matched":
        self.current_status = new_status
        self.set_form_status(self.current_status)
      
  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.current_status = None
    anvil.server.call('cancel',self.user.get_id())
    self.set_form_status(self.current_status)

  def complete_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.current_status = None
    anvil.server.call('match_complete',self.user.get_id())
    self.set_form_status(self.current_status)
    
  def set_form_status(self, user_status):
    if user_status == "requesting":
      self.status.text = "Status: Requesting empathy. Awaiting an offer..."
      self.set_jitsi_link("")
      self.complete_button.visible  =False
      self.cancel_button.visible = True
      self.request_button.visible = False
      self.offer_button.visible = False
    elif user_status == "offering":
      self.status.text = "Status: Offering empathy. Awaiting a request..."
      self.set_jitsi_link("")
      self.complete_button.visible = False
      self.cancel_button.visible = True
      self.request_button.visible = False
      self.offer_button.visible = False
    elif user_status == "matched":
      jitsi_code = anvil.server.call('get_code', self.user.get_id())
      self.status.text = "Use Jitsi to meet: "
      self.set_jitsi_link(jitsi_code)
      self.complete_button.visible = False
      self.cancel_button.visible = True
      self.request_button.visible = False
      self.offer_button.visible = False
    elif user_status == "empathy":
      jitsi_code = anvil.server.call('get_code', self.user.get_id())
      self.status.text = "Use Jitsi to meet: "
      self.set_jitsi_link(jitsi_code)
      self.complete_button.visible = True
      self.cancel_button.visible = False
      self.request_button.visible = False
      self.offer_button.visible = False
      new_status = anvil.server.call('match_commenced', self.user.get_id())
      if new_status != "empathy":
        assert new_status != "matched"
        self.user_status = new_status
        set_form_status(self, self.user_status)
    else:
      self.status.text = "Choose an option:"
      self.set_jitsi_link("")
      self.complete_button.visible = False
      self.cancel_button.visible = False
      self.request_button.visible = True
      self.offer_button.visible = True
    
  def set_jitsi_link(self, jitsi_code):
    if jitsi_code == "":
      self.jitsi_link.visible = False
      self.jitsi_link.text = ""
      self.jitsi_link.url = ""
    else:
      self.jitsi_link.url = "https://meet.jit.si/" + jitsi_code
      self.jitsi_link.text = self.jitsi_link.url
      self.jitsi_link.visible = True
    



  



