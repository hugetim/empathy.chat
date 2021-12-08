from ._anvil_designer import MatchFormTemplate
from anvil import *
import anvil.users
import anvil.server
from anvil.js import window, ExternalError
from ... import ui_procedures as ui
from ... import glob
from ... import helper as h
from .MyJitsi import MyJitsi
from .SliderPanel import SliderPanel


class MatchForm(MatchFormTemplate):
  state_keys = {'status'}
  
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
    #
    self.jitsi_embed = None
    self.timer_2.interval = 5

  def form_show(self, **event_args):
    """This method is called when the HTML panel is shown on the screen"""
    jitsi_code, duration, my_value = (
      anvil.server.call('init_match_form')
    )
    self.their_name = ""
    self.how_empathy_list = []
    self.set_jitsi_link(jitsi_code)
    self.chat_repeating_panel.items = []
    self.init_slider_panel(my_value)
    self.status = "init"
    self.update_status(self.item['status'])
    self.first_update = True
    self.update()
      
  def set_jitsi_link(self, jitsi_code):
    """Initialize or destroy embedded Jitsi Meet instance"""
    self.jitsi_link.url = "https://meet.jit.si/" + jitsi_code
    self.jitsi_link.text = jitsi_code
    self.jitsi_link.visible = True
    if not self.jitsi_embed:
      self.jitsi_embed = MyJitsi(item={'room_name': jitsi_code, 'name': glob.name})
      self.jitsi_column_panel.add_component(self.jitsi_embed)
    self.jitsi_column_panel.visible = True

  def init_slider_panel(self, my_value):
    if my_value:
      slider_item = {'visible': True, 'status': "submitted", 
                     'my_value': my_value, 'their_value': 5, 'their_name': ""}
    else:
      slider_item = {'visible': True, 'status': "waiting", 
                     'my_value': 5, 'their_value': 5, 'their_name': ""}
      self.slider_button_click()
    self.slider_panel = SliderPanel(item=slider_item)
    self.slider_column_panel.add_component(self.slider_panel)
    self.slider_panel.set_event_handler('x-hide', self.hide_slider)
    
  def update(self):
    status, self.how_empathy_list, self.their_name, new_items, their_value = (
      anvil.server.call_s('update_match_form')
    )
    self.update_status(status)
    self.slider_panel.update_name(self.their_name)
    self.update_messages(new_items)
    if self.slider_panel.item['status'] == "submitted" and their_value:
      self.slider_panel.receive_value(their_value)

  def update_status(self, status):
    if status != self.status:
      prev = self.status
      self.status = status
      matched = status == "matched"
      self.message_textbox.enabled = matched
      self.message_textbox.tooltip = (
        "" if matched else "Please wait until the other has joined before sending a message"
      )
      self.status_label.visible = self.status == "requesting"
      if self.status == "pinged":
        with h.PausedTimer(self.timer_2):
          with ui.BrowserTab("Someone waiting to join your empathy.chat", "_/theme/favicon-dot.ico"):
            ready = confirm("Someone has asked to join your empathy chat. Ready?")
          if ready:
            state = anvil.server.call('match_commit')
            self.update_status(state['status'])
          else:
            state = anvil.server.call('cancel')
            ui.reload()
      if prev != "matched" and self.status == "matched":
        self.slider_panel.item['status'] = None
        self.slider_panel.refresh_data_bindings()
      if not self.status:
        ui.reload()
      
  def update_messages(self, message_list):
    old_items = self.chat_repeating_panel.items
    messages_plus = []
    for i, how_empathy in enumerate(self.how_empathy_list):
      if how_empathy:
        mine = i == 0
        who = glob.name if mine else self.their_name
        messages_plus.append({
          "label": f"[from {who}'s profile]",
          "message": f"How {who} likes to receive empathy:\n{how_empathy}",
          "me": mine,
        })
    first_message = {True: True, False: True}
    for message in message_list:
      mine = message['me']
      if first_message[mine]:
        message['label'] = glob.name if mine else self.their_name
        first_message[mine] = False
    messages_plus += message_list
    if len(messages_plus) > len(old_items):
      self.chat_repeating_panel.items = messages_plus
      self.message_card.visible = True
      self.message_button.role = None
      self.call_js('scrollCard')
      if not self.first_update:
        self.chat_display_card.scroll_into_view()
      self.first_update = False
  
#   def chat_display_card_show(self, **event_args):
#     """This method is called when the column panel is shown on the screen"""
#     self.call_js('scrollCard')      
    
  def timer_2_tick(self, **event_args):
    """This method is called approx. once every 5 seconds, checking for messages"""
    self.update() 

  def message_textbox_pressed_enter(self, **event_args):
    text = self.message_textbox.text
    if text:
      _, _, _, temp, _ = anvil.server.call('add_chat_message', message=text)
      self.message_textbox.text = ""
      self.update_messages(temp)
      #self.call_js('scrollCard')
      
  def complete_button_click(self, **event_args):
    self.timer_2.interval = 0
    window.japi.executeCommand('hangup')
    state = anvil.server.call('match_complete')
    ui.reload()
    #self.top_form.reset_status(state)   

  def slider_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.slider_card.visible = not self.slider_card.visible
    self.slider_button.role = None if self.slider_card.visible else "raised"

  def hide_slider(self, **event_args):
    self.slider_card.visible = False
    self.slider_button.role = "raised"

  def message_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.message_card.visible = not self.message_card.visible
    self.message_button.role = None if self.message_button.role else "raised"

  def full_screen_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    try:
      if window.document.fullscreenElement:
          window.document.exitFullscreen()
      else:
          window.document.documentElement.requestFullscreen()
    except AttributeError as e:
      Notification("Full screen toggle blocked by browser. Try F11.").show()
      self.full_screen_button.enabled = False
      print(repr(e))
    except ExternalError as e:
      Notification("Full screen toggle blocked by browser. Try F11.").show()
      self.full_screen_button.enabled = False
      print(repr(e))

