from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.google.auth, anvil.google.drive
import anvil.server
import anvil.users
import parameters as p
import helper as h


class TimerForm(TimerFormTemplate):
  user_id = None
  status = None
  seconds_left = None

  def __init__(self, seconds_left, current_status, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
    # Any code you write here will run when the form opens.
    #if title:
    #  self.self.label_1.text = title
    self.seconds_left = seconds_left
    self.timer_label.text = ("Time left to confirm: "
                             + h.seconds_to_digital(self.seconds_left))
    self.status = current_status

  def timer_1_tick(self, **event_args):
    """This method is called Every 5.07 seconds"""
    new_status, lc, ps, tallies = anvil.server.call_s('get_status')
    if (self.status == "pinged" and new_status == "pinged"):
      self.seconds_left = h.seconds_left(new_status, lc, ps)
      self.status = new_status
    elif new_status != self.status:
      print (new_status)
      self.raise_event("x-close-alert", value=new_status)

  def timer_2_tick(self, **event_args):
    """This method is called Every 1 seconds. Does not trigger if [interval] is 0."""
    self.seconds_left -= 1
    self.timer_label.text = ("Time left to confirm: "
                             + h.seconds_to_digital(self.seconds_left))
    if self.seconds_left <= 0:
      self.raise_event("x-close-alert", value="timer elapsed")
