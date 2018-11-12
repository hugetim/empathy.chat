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
  confirm_wait_seconds = 60*15 # should be half of MatchMaker.prune.timeout
  current_status = None
  user_id = None
  seconds_left = None
  trust_level = 0
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)

    while not anvil.users.login_with_form():
      pass
    self.user_id = anvil.users.get_user().get_id()
    # 'prune' initializes new users to trust level 0 (via 'get_trust_level')
    t, s, match_start = anvil.server.call('prune',self.user_id)
    self.trust_level = t
    self.current_status = s
    if self.current_status == "matched":
      timer = datetime.datetime.now(match_start.tzinfo) - match_start
      self.seconds_left = self.confirm_match_seconds + self.buffer_seconds - timer.seconds
      if self.seconds_left<=0:
        self.current_status = anvil.server.call('cancel_other',self.user_id)
    elif self.current_status == "pinged":
      timer = datetime.datetime.now(match_start.tzinfo) - match_start
      self.seconds_left = self.confirm_match_seconds - timer.seconds
      if self.seconds_left<=0:
        anvil.server.call('cancel',self.user_id)
        self.current_status = None
      else:
        self.confirm_match()
        ## Old code for asking whether recent match still ongoing
        # conditional on status "empathy"
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
      request_type = 'requesting'
    else:
      request_type = 'offering'
    jitsi_code, last_confirmed = anvil.server.call('add_request',
                                                   self.user_id,
                                                   request_type)
    if jitsi_code == None:
      self.current_status = request_type
    else:
      timer = datetime.datetime.now(last_confirmed.tzinfo) - last_confirmed
      if timer.seconds > self.confirm_match_seconds:
        self.current_status = "matched"
        self.seconds_left = self.confirm_match_seconds + self.buffer_seconds
      else:
        self.current_status = "empathy"
    self.set_form_status(self.current_status) 

  def timer_1_tick(self, **event_args):
    """This method is called Every 5 seconds"""
    if self.current_status in ["requesting", "offering"]:
      new_status, match_start = anvil.server.call_s('get_status',self.user_id)
      if new_status == "pinged":
        self.current_status = new_status
        self.seconds_left = self.confirm_match_seconds
        self.confirm_match()
      elif new_status in ["empathy", None]:
        self.current_status = new_status
        self.set_form_status(self.current_status)
      elif new_status != self.current_status:
        print new_status
    elif self.current_status == "matched":
      new_status, match_start = anvil.server.call_s('get_status',self.user_id)
      if new_status == "requesting":
        alert("The empathy offer was canceled.")
        self.current_status = new_status
        self.set_form_status(self.current_status)
      elif new_status == "offering":
        alert("The empathy request was canceled.")
        self.current_status = new_status
        self.set_form_status(self.current_status)
      elif new_status == ["empathy",None]:
        self.current_status = new_status
        self.set_form_status(self.current_status)
      elif new_status != self.current_status:
        print new_status

  def timer_2_tick(self, **event_args):
    """This method is called Every 1 seconds"""
    if self.current_status in ["requesting", "offering"]:
      self.seconds_left -= 1
      if self.seconds_left<=0:
        self.confirm_wait()
    elif self.current_status == "matched":
      self.seconds_left -= 1
      self.timer_label.text = ("A match has been found and they have up to " 
                               + str(self.seconds_left) + " seconds to confirm.")
      if self.seconds_left<=0:
        self.current_status = anvil.server.call('cancel_other',self.user_id)
        self.set_form_status(self.current_status)
    
  
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
    if user_status:
      self.request_button.visible = False
      self.drop_down_1.enabled = False
      self.drop_down_1.foreground = "gray"
      if user_status in ["requesting","offering"]:
        self.status.text = ("Status: Requesting an empathy exchange. "
                            + "Awaiting a match...")
        self.status.bold = False
        self.set_jitsi_link("")
        self.complete_button.visible = False
        self.cancel_button.visible = True
        self.set_drop_down(user_status)
        self.seconds_left = self.confirm_wait_seconds
      else:
        assert user_status in ["matched", "empathy"]
        self.cancel_button.visible = False        
        if user_status=="matched":
          self.timer_label.text = ("A match has been found and they have up to " 
                                   + str(self.seconds_left) + " seconds to confirm.")
          self.timer_label.visible = True
          self.status.text = "A match should be ready soon. Set up Jitsi at: "
          self.status.bold = False
          jitsi_code, request_type = anvil.server.call('get_code', self.user_id)
          self.complete_button.visible = False
        else:
          assert user_status=="empathy"
          self.timer_label.visible = False
          (new_status, match_start,  
           jitsi_code, request_type) = anvil.server.call('match_commenced',
                                                         self.user_id)
          if new_status != "empathy":
            assert new_status != "matched"
            self.current_status = new_status
            return self.set_form_status(self.current_status)
          self.status.text = "You have a confirmed match. Use Jitsi to meet: "
          self.status.bold = True
          self.complete_button.visible = True
        self.set_jitsi_link(jitsi_code)     
        self.set_drop_down(request_type)
    else:
      self.status.text = "Request a match when ready:"
      self.status.bold = True
      self.set_jitsi_link("")
      self.timer_label.visible = False
      self.complete_button.visible = False
      self.cancel_button.visible = False
      self.request_button.visible = True
      self.drop_down_1.enabled = True
      self.drop_down_1.foreground = "black"
    
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
    out = confirm(content=f,
                  title="A match is available. Are you ready?",
                  large=False,
                  dismissible=False)
    if out==True:
      self.current_status = "empathy"
    elif out==False:
      anvil.server.call('cancel',self.user_id)
      self.current_status = None
    elif out=="timer elapsed":
      anvil.server.call('cancel',self.user_id)
      self.current_status = None
      alert("A match was found, but the time available for you to confirm ("
            + str(self.confirm_match_seconds) + ") has elapsed.",
            dismissible=False)
    else:
      print out
      assert out in [None,"requesting","offering"]
      self.current_status = out
    self.set_form_status(self.current_status)
    
    #open_form('ConfirmForm', self.seconds_left, self.user_id,
    #          "A match is available. Are you ready?")

  def confirm_wait(self):
    assert self.current_status in ["requesting", "offering"]
    f = TimerForm(self.confirm_wait_seconds, self.user_id, self.current_status)
    out = confirm(content=f,
                  title="Continue waiting for a match?",
                  large=False,
                  dismissible=False)
    if out==True:
      anvil.server.call('confirm_wait',self.user_id)
      #seconds_left reset by set_form_status() below
    elif out==False:
      anvil.server.call('cancel',self.user_id)
      self.current_status = None
    elif out=="timer elapsed":
      anvil.server.call('cancel',self.user_id)
      self.current_status = None
      alert("Request canceled due to failure to confirm within "
            + str(self.confirm_wait_seconds) + " seconds.",
            dismissible=False)
    else:
      print out
      assert out in ["pinged","empathy"]
      self.current_status = out
      if out=="pinged":
        self.seconds_left = self.confirm_match_seconds
        self.confirm_match()
    self.set_form_status(self.current_status)

  def set_drop_down(self, request_type):
    if request_type=="requesting":
      self.drop_down_1.selected_value = "Not ready to offer empathy first"
    else:
      assert request_type=="offering"
      self.drop_down_1.selected_value = "Willing to offer empathy first"
      