from ._anvil_designer import MatchFormTemplate
from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.server
from .MyJitsi import MyJitsi
from .SliderPanel import SliderPanel


class MatchForm(MatchFormTemplate):
  state_keys = {}
  
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
    #
    self.jitsi_embed = None
    self.timer_2.interval = 5

  def form_show(self, **event_args):
    """This method is called when the HTML panel is shown on the screen"""
    self.top_form = get_open_form()
    jitsi_code, duration = anvil.server.call('get_code')
    self.set_jitsi_link(jitsi_code)
    slider_item = {'visible': True, 'status': None, 'my_value': 5, 'their_value': 5}
    self.slider_panel = SliderPanel(item=slider_item)
    self.slider_column_panel.add_component(self.slider_panel)
      
  def set_jitsi_link(self, jitsi_code):
    """Initialize or destroy embedded Jitsi Meet instance"""
    self.jitsi_link.url = "https://meet.jit.si/" + jitsi_code
    self.jitsi_link.text = jitsi_code
    self.jitsi_link.visible = True
    if not self.jitsi_embed:
      self.jitsi_embed = MyJitsi(item={'room_name': jitsi_code, 'name': self.top_form.item['name']})
      self.jitsi_column_panel.add_component(self.jitsi_embed)
    self.jitsi_column_panel.visible = True
    self.chat_repeating_panel.items, their_value = anvil.server.call_s('get_messages')
    self.chat_display_card.visible = True
    self.chat_send_card.visible = True

  def chat_display_card_show(self, **event_args):
    """This method is called when the column panel is shown on the screen"""
    self.call_js('scrollCard')      
    
  def timer_2_tick(self, **event_args):
    """This method is called approx. once every 5 seconds, checking for messages"""
    old_items = self.chat_repeating_panel.items
    new_items, their_value = anvil.server.call_s('get_messages')
    if len(new_items) > len(old_items):
      self.chat_repeating_panel.items = new_items
      self.call_js('scrollCard')
      self.chat_display_card.scroll_into_view()   
    if self.slider_panel.item['status'] == "submitted" and their_value:
      self.slider_panel.receive_value(their_value)
      

  def message_textbox_pressed_enter(self, **event_args):
    temp = anvil.server.call('add_message', message=self.message_textbox.text)
    self.message_textbox.text = ""
    self.chat_repeating_panel.items = temp
    self.call_js('scrollCard')

  def complete_button_click(self, **event_args):
    state = anvil.server.call('match_complete')
    self.top_form.reset_status(state)   
