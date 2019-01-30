from anvil import *
import anvil.google.auth, anvil.google.drive
import anvil.server
import anvil.users
import parameters as p
import helper as h


class TimerForm(TimerFormTemplate):
  user_id = None
  status = None
  seconds_left = None

  def __init__(self, seconds_left, user_id, current_status, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
    # Any code you write here will run when the form opens.
    #if title:
    #  self.self.label_1.text = title
    self.seconds_left = seconds_left
    self.timer_label.text = str(self.seconds_left) + " seconds left to confirm."
    self.user_id = user_id
    self.status = current_status

  def timer_1_tick(self, **event_args):
    """This method is called Every 5.07 seconds"""
    new_status, lc, ps, tallies = anvil.server.call_s('get_status',self.user_id)
    if (self.status in ["pinged-one", "pinged-mult"]
        and new_status in ["pinged-one", "pinged-mult"]):
      old_seconds_left = self.seconds_left
      self.seconds_left = h.seconds_left(new_status, lc, ps)
      if self.seconds_left > old_seconds_left + p.BUFFER_SECONDS:
        Notification("You are now the only match available, so you have more time to respond.",
                     title="Time added").show()
      elif self.seconds_left < old_seconds_left - p.BUFFER_SECONDS:
        Notification("Another person is now available to take your place if you are not able"
                     + " to respond within two minutes.",
                     title="Prompt response needed").show()
      self.status = new_status
    elif new_status != self.status:
      print (new_status)
      self.raise_event("x-close-alert", value=new_status)

  def timer_2_tick(self, **event_args):
    """This method is called Every 1 seconds. Does not trigger if [interval] is 0."""
    self.seconds_left -= 1
    self.timer_label.text = str(self.seconds_left) + " seconds left to confirm."
    if self.seconds_left <= 0:
      if self.status in ["pinged-mult", "pinging-mult"]:
        self.raise_event("x-close-alert", value="alt timer elapsed")
      else:
        self.raise_event("x-close-alert", value="timer elapsed")
