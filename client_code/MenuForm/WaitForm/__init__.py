from ._anvil_designer import WaitFormTemplate
from anvil import *
import anvil.users
import anvil.server
from ... import helper as h


class WaitForm(WaitFormTemplate):
  state_keys = {'status'}
  
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
    #
    self.timer_2.interval = 5

  def form_show(self, **event_args):
    """This method is called when the HTML panel is shown on the screen"""
    self.top_form = get_open_form()
    if self.item['status'] != "pinging":
      h.warning(f"{self.item['status']} != 'pinging'")

  def reset_status(self, state):
    """Reset WaitForm status, removing from parent if needed"""
    self.top_form.reset_status(state)
    
  def cancel_button_click(self, **event_args):
    state = anvil.server.call('cancel_accept')
    self.reset_status(state)

  def timer_2_tick(self, **event_args):
    """This method is called every 5 seconds, checking for status changes"""
    if self.item['status'] == "pinging":
      state = anvil.server.call_s('get_status')
      if state['status'] != self.item['status']:
        self.reset_status(state)
