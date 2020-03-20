from ._anvil_designer import MatchFormTemplate
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


class MatchForm(MatchFormTemplate):
  def __init__(self, dd_items, rt, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
    #
    self.drop_down_1.items = dd_items
    self.drop_down_1.selected_value = rt
    self.jitsi_embed = None
    self.top_form = get_open_form()

  def complete_button_click(self, **event_args):
    self.set_seconds_left(None)
    self.tallies = anvil.server.call('match_complete')
    self.reset_status()
      
  def set_jitsi_link(self, jitsi_code):
    """Initialize or destroy embedded Jitsi Meet instance"""
    if jitsi_code == "":
      self.jitsi_column_panel.visible = False
      if self.jitsi_embed:
        self.jitsi_embed.remove_from_parent()
        self.jitsi_embed = None
      self.chat_display_card.visible = False
      self.chat_send_card.visible = False
      self.jitsi_link.visible = False
      self.jitsi_link.text = ""
      self.jitsi_link.url = ""
      self.test_link.visible = True
    else:
      self.jitsi_link.url = "https://meet.jit.si/" + jitsi_code
      self.jitsi_link.text = jitsi_code
      self.jitsi_link.visible = True
      if not self.jitsi_embed:
        self.jitsi_embed = MyJitsi(jitsi_code)
        self.jitsi_column_panel.add_component(self.jitsi_embed)
      self.jitsi_column_panel.visible = True
      self.test_link.visible = False
      self.chat_repeating_panel.items = anvil.server.call_s('get_messages')
      self.chat_display_card.visible = True
      self.chat_send_card.visible = True

  def chat_display_card_show(self, **event_args):
    """This method is called when the column panel is shown on the screen"""
    self.call_js('scrollCard')   

  def message_textbox_pressed_enter(self, **event_args):
    temp = anvil.server.call('add_message', message=self.message_textbox.text)
    self.message_textbox.text = ""
    self.chat_repeating_panel.items = temp
    self.call_js('scrollCard')
