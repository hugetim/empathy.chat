from ._anvil_designer import WaitFormTemplate
from anvil import *
import anvil.facebook.auth
import anvil.users
import anvil.server
from ... import parameters as p
from ... import helper as h


class WaitForm(WaitFormTemplate):
  state_keys = {'status', 'seconds_left'}
  
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
    #
    self.set_seconds_left(self.item['status'], self.item['seconds_left'])
    self.timer_1.interval = 1
    self.timer_2.interval = 1

  def form_show(self, **event_args):
    """This method is called when the HTML panel is shown on the screen"""
    self.top_form = get_open_form()
    if self.item['status'] != "pinging":
      print(f"Warning: {self.item['status']} != 'pinging'")
    self.status_label.text = ("Potential match available. Time left for them "
                              + "to confirm:  "
                              + h.seconds_to_digital(self.item['seconds_left']))

  def reset_status(self, state):
    """Reset WaitForm status, removing from parent if needed"""
    old_status = self.item['status']
    self.set_seconds_left(state['status'], state['seconds_left'])
    if old_status != state['status']:
      self.top_form.reset_status(state)
    
  def set_seconds_left(self, new_status=None, new_seconds_left=None):
    """Set status and related time variables"""
    self.last_5sec = h.now()
    if new_status and new_status != "matched":
      self.item['seconds_left'] = new_seconds_left
      if self.item['status'] == "pinging" and new_status == "requesting":
        self.item['seconds_left'] = max(self.item['seconds_left'], 
                                        p.BUFFER_SECONDS)
    #print('before status change: ', self.item['seconds_left'])
    self.item['status'] = new_status          
      
  def cancel_button_click(self, **event_args):
    state = anvil.server.call('cancel')
    self.reset_status(state)

  def timer_1_tick(self, **event_args):
    """This method is called once per second, updating countdowns"""
    if self.item['status'] == "pinging" and self.item['seconds_left'] > 0:
      self.item['seconds_left'] -= 1
      self.status_label.text = ("Potential match available. Time left for them "
                                + "to confirm:  "
                                + h.seconds_to_digital(self.item['seconds_left']))

  def timer_2_tick(self, **event_args):
    """This method is called approx. once per second, checking for status changes"""
    now=h.now()
    # Run this code approx. once a second
    if self.item['status'] == "pinging" and self.item['seconds_left'] <= 0:
      self.reset_status(anvil.server.call('cancel_other'))
    if (now - self.last_5sec).total_seconds() > 4.5:
      # Run this code every 5 seconds
      self.last_5sec = now
      if self.item['status'] == "pinging":
        state = anvil.server.call_s('get_status')
        if state['status'] != self.item['status']:
          self.reset_status(state)
