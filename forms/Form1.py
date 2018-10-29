from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.server
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.users
import datetime
from TimerForm import TimerForm

class Form1(Form1Template):
  buffer_seconds = 5
  confirm_match_seconds = 60
  confirm_wait_seconds = 60*15
  assume_empathy_complete_s = 60*60*8
  current_status = None
  user_id = None
  seconds_left = None
  trust_level = 0
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    
    while not anvil.users.login_with_form():
      pass
    self.user_id = anvil.users.get_user().get_id()
    # initialize new users
    self.trust_level = anvil.server.call('get_trust_level',self.user_id)
    self.current_status = anvil.server.call('prune_matching',self.user_id)
    if self.current_status == "matched":
      match_start = anvil.server.call('get_match_start', 
                                           self.user_id)
      if match_start == None:
        # matching data table indicates no longer matched
        self.current_status = anvil.server.call('get_status',
                                                self.user_id)
      else:
        timer = datetime.datetime.now(match_start.tzinfo) - match_start
        self.seconds_left = self.confirm_match_seconds + self.buffer_seconds - timer.seconds
        print timer.seconds
    elif self.current_status == "pinged":
      match_start = anvil.server.call('get_match_start', 
                                           self.user_id)
      if match_start == None:
        # matching data table indicates no longer matched
        self.current_status = anvil.server.call('get_status',
                                                self.user_id)
      else:
        timer = datetime.datetime.now(match_start.tzinfo) - match_start
        self.seconds_left = self.confirm_match_seconds - timer.seconds
        self.confirm_match()
    
    ## separate if statement allows for status upgrade from initial "matched"
    if self.current_status == "empathy":
      match_start = anvil.server.call('get_match_start', 
                                           self.user_id)
      timer = datetime.datetime.now(match_start.tzinfo) - match_start
      if timer.seconds > self.assume_empathy_complete_s:
        self.current_status = None
        anvil.server.call('match_complete',self.user_id)
        #ongoing = confirm("Is your empathy session, begun "
        #                  + str(timer.seconds/60)
        #                  + " minutes ago, still ongoing?")
        #  if ongoing:
        #    self.current_status = "empathy"
        #  else:
        #    self.current_status = None
        #    anvil.server.call('match_complete',self.user_id)
    self.set_form_status(self.current_status)
    
  def request_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if self.drop_down_1.selected_value=="Not ready to offer empathy first":
      jitsi_code = anvil.server.call('add_request',self.user_id)
      if jitsi_code == None:
        self.current_status = "requesting"
      else:
        self.current_status = "matched"
        self.seconds_left = self.confirm_match_seconds + self.buffer_seconds
    else:
      jitsi_code = anvil.server.call('add_offer',self.user_id)
      if jitsi_code == None:
        self.current_status = "offering"
      else:
        self.current_status = "matched"
        self.seconds_left = self.confirm_match_seconds + self.buffer_seconds
    self.set_form_status(self.current_status) 

  def timer_1_tick(self, **event_args):
    """This method is called Every 5 seconds"""
    if self.current_status in ["requesting", "offering"]:
      new_status = anvil.server.call('get_status',self.user_id)
      if new_status == "matched":
        self.seconds_left = self.confirm_match_seconds
        self.confirm_match()
      elif self.current_status == "matched":
        pass
      new_status = anvil.server.call('get_status',self.user_id)
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
      self.status.text = "Status: Requesting to receive empathy first. Awaiting an offer..."
      self.set_jitsi_link("")
      self.complete_button.visible  =False
      self.cancel_button.visible = True
      self.request_button.visible = False
      self.offer_button.visible = False
      self.seconds_left = self.confirm_wait_seconds
    elif user_status == "offering":
      self.status.text = "Status: Requesting an empathy exchange. Awaiting a match..."
      self.set_jitsi_link("")
      self.complete_button.visible = False
      self.cancel_button.visible = True
      self.request_button.visible = False
      self.offer_button.visible = False
      self.seconds_left = self.confirm_wait_seconds
    elif user_status == "matched":
      self.timer_label = ("A match has been found and they have up to " 
                          + self.seconds_left + " seconds to confirm.")
      self.status.text = "A match should be ready soon. Set up Jitsi at: "
      jitsi_code = anvil.server.call('get_code', self.user_id)
      self.set_jitsi_link(jitsi_code)
      self.timer_label.visible = True
      self.complete_button.visible = False
      self.cancel_button.visible = False
      self.request_button.visible = False
      self.offer_button.visible = False
    elif user_status == "empathy":
      self.timer_label.visible = False
      self.status.text = "You have a confirmed match. Use Jitsi to meet: "
      jitsi_code = anvil.server.call('get_code', self.user_id)
      self.set_jitsi_link(jitsi_code)
      self.complete_button.visible = True
      self.cancel_button.visible = False
      self.request_button.visible = False
      self.offer_button.visible = False
      new_status = anvil.server.call('match_commenced', self.user_id)
      if new_status != "empathy":
        assert new_status != "matched"
        self.current_status = new_status
        self.set_form_status(self.current_status)
    else:
      self.status.text = "Choose an option:"
      self.set_jitsi_link("")
      self.timer_label.visible = False
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
    
  def confirm_match(self):
    assert self.current_status=="pinged"
    f = TimerForm(self.seconds_left, self.user_id, self.current_status)
    out = alert(content=f,
                title="A match is available. Are you ready?",
                large=True,
                dismissible=False)
    if out=="Yes":
      anvil.server.call('match_commenced',self.user_id)
      self.current_status = "empathy"
    elif out=="No":
      anvil.server.call('cancel',self.user_id)
      self.current_status = None
    elif out=="timer elapsed":
      anvil.server.call('cancel',self.user_id)
      self.current_status = None
      alert("A match was found, but the time available for you to confirm has elapsed.")
    else
      assert out in [None,"requesting","offering"]
      self.current_status = out
    self.set_form_status(self.current_status)
    
    #open_form('ConfirmForm', self.seconds_left, self.user_id,
    #          "A match is available. Are you ready?")







  



