from ._anvil_designer import TimerFormTemplate
from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.server
from .... import helper as h


class TimerForm(TimerFormTemplate):
  def __init__(self, seconds_left, current_status, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
    # Any code you write here will run when the form opens.
    #if title:
    #  self.self.label_1.text = title
    self.seconds_left = seconds_left
    self.timer_label.text = ("Time left to confirm:  "
                             + h.seconds_to_digital(self.seconds_left))
    self.status = current_status
    self.last_5sec = h.now()

  def timer_1_tick(self, **event_args):
    """This method is called Every 1 seconds"""
    if self.seconds_left > 0:
      self.seconds_left -= 1
      self.timer_label.text = ("Time left to confirm:  "
                               + h.seconds_to_digital(self.seconds_left))

  def timer_2_tick(self, **event_args):
    """This method is called Every 1 seconds. Does not trigger if [interval] is 0."""
    now = h.now()
    # Run this code once a second
    if (now - self.last_5sec).seconds > 4.5:
      # Run this code every 5 seconds
      self.last_5sec = now
      state = anvil.server.call_s('get_status')
      new_status = state['status']
      print("new_status:", new_status)
      if new_status != self.status:
        print("new_status:", new_status)
        self.raise_event("x-close-alert", value=new_status)
    if self.seconds_left <= 0:
      self.raise_event("x-close-alert", value="timer elapsed")