from ._anvil_designer import DashFormTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tz
from .TimerForm import TimerForm
from .MyJitsi import MyJitsi
from .. import parameters as p
from .. import helper as h
import random


class DashForm(DashFormTemplate):
  def __init__(self, dd_items, rt, tallies, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
    
    self.drop_down_1.items = dd_items
    self.drop_down_1.selected_value = rt
    self.tallies = tallies
    self.timer_2.interval = 5
    self.top_form = get_open_form()
       
  def request_button_click(self, **event_args):
    request_type = self.drop_down_1.selected_value
    self.top_form.request_button_click(request_type)

  def timer_2_tick(self, **event_args):
    """This method is called every 5 seconds, checking for status changes"""
    # Run this code approx. once a second
    self.tallies = anvil.server.call_s('get_tallies')
    self.update_tally_label()

  def form_show(self, **event_args):
    """This method is called when the HTML panel is shown on the screen"""
    self.update_tally_label()

  def update_tally_label(self):
    """Update form based on tallies state"""
    if self.tallies['will_offer_first'] == 0 and self.tallies['receive_first'] == 0:
      self.tally_label.font_size = 12
    else:
      self.tally_label.font_size = None
    self.tally_label.text = h.tally_text(self.tallies)
    if len(self.tally_label.text) > 0:
      self.tally_label.visible = True
      self.note_label.text = ""
      self.note_label.visible = False
    else:
      self.tally_label.visible = False
      if self.request_em_check_box.checked:
        self.note_label.text = ""
        self.note_label.visible = False
      else:
        self.note_label.text = "Note: In the Settings menu (upper left), you can opt-in to receive an email notification when someone else requests empathy."
        self.note_label.visible = True
