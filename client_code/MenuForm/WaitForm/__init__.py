from ._anvil_designer import WaitFormTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tz
from .TimerForm import TimerForm
from .MyJitsi import MyJitsi
from .DashForm import DashForm
from .. import parameters as p
from .. import helper as h
import random


class WaitForm(WaitFormTemplate):
  def __init__(self, dd_items, rt, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
    #
    self.drop_down_1.items = dd_items
    self.drop_down_1.selected_value = rt
    self.timer_1.interval = 1
    self.top_form = get_open_form()

  def renew_button_click(self, **event_args):
    self.confirm_wait()

  def cancel_button_click(self, **event_args):
    self.set_seconds_left(None)
    self.tallies = anvil.server.call('cancel')
    self.reset_status()

  def timer_1_tick(self, **event_args):
    """This method is called once per second, updating countdowns"""
    if self.status == "requesting" and self.seconds_left > 0:
      self.seconds_left -= 1
      self.timer_label.text = ("Your request will expire in:  "
                               + h.seconds_to_digital(self.seconds_left) )
    elif self.status == "pinging" and self.seconds_left > 0:
      self.seconds_left -= 1
      self.status_label.text = ("Potential match available. Time left for them "
                                + "to confirm:  "
                                + h.seconds_to_digital(self.seconds_left))

  def confirm_match(self, seconds):
    f = TimerForm(seconds, self.status)
    out = alert(content=f,
                title="A match is available. Are you ready?",
                large=False,
                dismissible=False,
                buttons=[("Yes", True), ("No", False)])
    if out == True:
      self.status = "matched"
      s, sl, self.tallies = anvil.server.call('match_commenced')
      self.set_seconds_left(s, sl)
    elif out in [False, "timer elapsed"]:
      self.tallies = anvil.server.call('cancel')
      self.set_seconds_left(None)
      if out == "timer elapsed":
        alert("A match was found, but the time available for you to confirm ("
              + h.seconds_to_words(p.CONFIRM_MATCH_SECONDS) + ") elapsed.",
              dismissible=False)
    elif out is None:
      self.tallies = anvil.server.call_s('get_tallies')
      self.set_seconds_left(None)
    else:
      print(out)
      assert out == "requesting"
      s, sl, self.tallies = anvil.server.call_s('get_status')
      self.set_seconds_left(s, sl)
    self.reset_status()
      
  def pinged_em_check_box_change(self, **event_args):
    """This method is called when this checkbox is checked or unchecked"""
    checked = self.pinged_em_check_box.checked
    s, sl, t = anvil.server.call('set_pinged_em', checked)
    self.set_seconds_left(s, sl)
    self.tallies = t
    self.reset_status()
