from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.server
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.users
import datetime

class Form1(Form1Template):
  confirm_seconds = 60
  current_status = None
  user_id = None
  match_start = None 
  seconds_left = None
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    
    while not anvil.users.login_with_form():
      pass
    user = anvil.users.get_user()
    self.user_id = user.get_id()
    self.current_status = anvil.server.call('get_status',self.user_id)
    if self.current_status == "matched":
      self.match_start = anvil.server.call('get_match_start', 
                                           self.user_id)
      if self.match_start == None:
        # matching data table indicates no longer matched
        self.current_status = anvil.server.call('get_status',
                                                self.user_id)
      else:
        timer = datetime.datetime.now(self.match_start.tzinfo) - self.match_start
        self.seconds_left = timer.seconds
        print timer.seconds
        if timer.seconds > self.seconds_to_cancel:
          ongoing = confirm("Is your empathy session, begun "
                            + str(timer.seconds/60)
                            + " minutes ago, still ongoing?")
          if ongoing:
            self.current_status = "empathy"
          else:
            self.current_status = None
            anvil.server.call('match_complete',self.user_id)
    self.set_form_status(self.current_status)
    # initialize new users
    anvil.server.call('get_trust_level',self.user_id)

  def request_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    jitsi_code = anvil.server.call('add_request',self.user_id)
    if jitsi_code == None:
      self.current_status = "requesting"
    else:
      self.match_start = datetime.datetime.now()
      self.current_status = "matched"
    self.set_form_status(self.current_status)

  def offer_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    jitsi_code = anvil.server.call('add_offer',self.user_id)
    if jitsi_code == None:
      self.current_status = "offering"
    else:
      self.match_start = datetime.datetime.now()
      self.current_status = "matched"
    self.set_form_status(self.current_status) 

  def timer_1_tick(self, **event_args):
    """This method is called Every 5 seconds"""
    if self.current_status in ["requesting", "offering"]:
      new_status = anvil.server.call('get_status',self.user_id)
      if new_status == "matched":
        open_form('ConfirmForm', self.confirm_seconds, self.user_id,
                  "A match is available. Are you ready?")
    elif self.current_status == "matched":
      new_status = anvil.server.call('get_status',self.user_id)
      timer = datetime.datetime.now(self.match_start.tzinfo) - self.match_start
      print timer.seconds
      if new_status=="matched":
        if timer.seconds > self.seconds_to_cancel:
          new_status = "empathy"
      else:
        if new_status == "requesting":
          alert("The empathy offer was canceled.")
        if new_status == "offering":
          alert("The empathy request was canceled.")
        self.current_status = new_status
      self.set_form_status(self.current_status)

  def timer_2_tick(self, **event_args):
    """This method is called Every 1 seconds"""
    pass
  
  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.current_status = None
    anvil.server.call('cancel',self.user_id)
    self.set_form_status(self.current_status)

  def complete_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.current_status = None
    anvil.server.call('match_complete',self.user_id)
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
      jitsi_code = anvil.server.call('get_code', self.user_id)
      self.status.text = "Use Jitsi to meet: "
      self.set_jitsi_link(jitsi_code)
      self.complete_button.visible = False
      self.cancel_button.visible = True
      self.request_button.visible = False
      self.offer_button.visible = False
    elif user_status == "empathy":
      jitsi_code = anvil.server.call('get_code', self.user_id)
      self.status.text = "Use Jitsi to meet: "
      self.set_jitsi_link(jitsi_code)
      self.complete_button.visible = True
      self.cancel_button.visible = False
      self.request_button.visible = False
      self.offer_button.visible = False
      new_status = anvil.server.call('match_commenced', self.user_id)
      if new_status != "empathy":
        assert new_status != "matched"
        self.current_status = new_status
        set_form_status(self, self.current_status)
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
    








  



