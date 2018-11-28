from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.server
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.users

class TimerForm(TimerFormTemplate):
  seconds_left = None
  user_id = None
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
    new_status, match_start, n = anvil.server.call_s('get_status',self.user_id)
    if new_status != self.current_status:
      print new_status
      self.raise_event("x-close-alert", value=new_status)

  def timer_2_tick(self, **event_args):
    """This method is called Every 1 seconds. Does not trigger if [interval] is 0."""
    self.seconds_left -= 1
    self.timer_label.text = str(self.seconds_left) + " seconds left to confirm."
    if self.seconds_left == 0:
      self.raise_event("x-close-alert", value="timer elapsed")

  #def return_back(self, confirmed):
  #  if confirmed:
  #    anvil.server.call('match_commenced',self.user_id)
  #    open_form('Form1')
  #  else:
  #    anvil.server.call('cancel',self.user_id)
  #    open_form('Form1')  
  



