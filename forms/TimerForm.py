from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.server
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.users
import parameters as p
import datetime

class TimerForm(TimerFormTemplate):
  seconds_left = None
  user_id = None
  alt_avail = None
  def __init__(self, seconds_left, user_id, current_status, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
    # Any code you write here will run when the form opens.
    #if title:
    #  self.self.label_1.text = title
    self.seconds_left = seconds_left
    self.timer_label.text = str(self.seconds_left) + " seconds left to confirm."
    self.user_id = user_id
    self.current_status = current_status

  #def button_yes_click(self, **event_args):
  #  """This method is called when the button is clicked"""
  #  self.raise_event("x-close-alert", value="Yes")

  #def button_no_click(self, **event_args):
  #  """This method is called when the button is clicked"""
  #  self.raise_event("x-close-alert", value="No")

  def timer_1_tick(self, **event_args):
    """This method is called Every 5 seconds"""
    new_status, ref_time, n, alt_avail = anvil.server.call_s('get_status',self.user_id)
    self.alt_avail = alt_avail
    if new_status != self.current_status:
      if alt_avail==True:
        new_status = "alt " + new_status
      print new_status
      self.raise_event("x-close-alert", value=new_status)
    else:
      timer = datetime.datetime.now(ref_time.tzinfo) - ref_time
      if self.current_status=="pinged":
        seconds_left = self.seconds_left
        if alt_avail:
          self.seconds_left = min(p.CONFIRM_MATCH_SECONDS - timer.seconds, seconds_left)
        else:
          self.seconds_left = max(p.CONFIRM_WAIT_SECONDS - timer.seconds, seconds_left)
        if self.seconds_left > seconds_left + p.BUFFER_SECONDS:
          Notification("You are now the only match available, so you have more time to respond.",
                       title="Time added").show()
        elif self.seconds_left < seconds_left - p.BUFFER_SECONDS:
          Notification("Another person is now available to take your place if you are not able"
                       + " to respond within two minutes.",
                       title="Prompt response needed").show()

  def timer_2_tick(self, **event_args):
    """This method is called Every 1 seconds. Does not trigger if [interval] is 0."""
    self.seconds_left -= 1
    self.timer_label.text = str(self.seconds_left) + " seconds left to confirm."
    if self.seconds_left <= 0:
      if alt_avail==True:
        self.raise_event("x-close-alert", value="alt timer elapsed")
      else:
        self.raise_event("x-close-alert", value="timer elapsed")

  #def return_back(self, confirmed):
  #  if confirmed:
  #    anvil.server.call('match_commenced',self.user_id)
  #    open_form('Form1')
  #  else:
  #    anvil.server.call('cancel',self.user_id)
  #    open_form('Form1')  
  



