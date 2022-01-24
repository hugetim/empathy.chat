from ._anvil_designer import MatchFormTemplate
from anvil import *
import anvil.users
import anvil.server
from anvil.js import window, ExternalError
from pdf_viewer.pdf_viewer import pdf_viewer
from ... import ui_procedures as ui
from ... import glob
from ... import helper as h
from ... import parameters as p
from .MyJitsi import MyJitsi
from .SliderPanel import SliderPanel
from .MobileAlert import MobileAlert


class MatchForm(MatchFormTemplate):
  state_keys = {'status'}
  
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
    #
    self.timer_2.interval = 0
    self.jitsi_embed = None
    self._info_clicked = False
    self.info_button.role = ""
    self.their_external = False
    self.their_complete = False
    self.lists_url = ""

  def form_show(self, **event_args):
    """This method is called when the HTML panel is shown on the screen"""
    self.proptime_id, jitsi_code, duration, my_value = (
      anvil.server.call('init_match_form')
    )
    self.their_name = ""
    self.how_empathy_list = []
    self.my_timer_1.minutes = (duration - 5)/2
    self.set_jitsi_link(jitsi_code)
    self.chat_repeating_panel.items = []
    self.init_slider_panel(my_value)
    self.status = "init"
    self.update_status(self.item['status'])
    self.first_update = True
    self.update()
    if glob.MOBILE:
      alert(content=MobileAlert(), title="Attention mobile users", large=True)
    self._first_tick = True
    self.timer_2.interval = 5

  def set_jitsi_link(self, jitsi_code):
    """Initialize or destroy embedded Jitsi Meet instance"""
    # https://jitsi.github.io/handbook/docs/user-guide/user-guide-advanced
    base = "https://meet.jit.si/" if p.DEBUG_MODE else "https://8x8.vc/vpaas-magic-cookie-848c456481fc4755aeb61d02b9d9dab2/"
    self.jitsi_link.url = base + jitsi_code + "#config.prejoinPageEnabled=false"
    self.jitsi_link.text = "" #jitsi_code
    self.jitsi_code = jitsi_code
    self.jitsi_link.visible = True
    self.add_jitsi_embed()
    self.jitsi_column_panel.visible = True
    
  def add_jitsi_embed(self):
    if not self.jitsi_embed:
      self.jitsi_embed = MyJitsi(item={'room_name': self.jitsi_code, 'name': glob.name})
      self.jitsi_column_panel.add_component(self.jitsi_embed)

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
    match_state = anvil.server.call_s('update_match_form')
    self.how_empathy_list = match_state['how_empathy_list']
    self.their_name = match_state['their_name']
    self.update_status(match_state['status'])
    self.slider_panel.update_name(self.their_name)
    self.update_messages(match_state['message_items'])
    their_value = match_state['their_value']
    if self.slider_panel.item['status'] == "submitted" and their_value:
      self.slider_panel.receive_value(their_value)
    self.update_their_external(match_state['their_external'])
    self.update_their_complete(match_state['their_complete'])

  def update_status(self, status):
    if status != self.status:
      prev = self.status
      self.status = status
      matched = status == "matched"
      self.message_textbox.enabled = matched
      self.message_textbox.tooltip = (
        "" if matched else "Please wait until the other has joined before sending a message"
      )
      self.complete_button.visible = True
      self.complete_button.text = "End Chat" if matched else "Cancel"
      self.status_label.visible = self.status == "requesting"
      if self.status == "pinged":
        with h.PausedTimer(self.timer_2):
          with ui.BrowserTab("Someone waiting to join your empathy.chat", "_/theme/favicon-dot.ico"):
            ready = confirm("Someone has asked to join your empathy chat. Ready?")
          if ready:
            state = anvil.server.call('match_commit')
            self.update_status(state['status'])
            anvil.server.call_s('update_my_external', bool(self.jitsi_embed))
          else:
            state = anvil.server.call('cancel_now', self.proptime_id)
            ui.reload()
      if prev != "matched" and self.status == "matched":
        self.slider_panel.item['status'] = None
        self.slider_panel.update_status()
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

  def update_their_external(self, their_external):
    if bool(their_external) != self.their_external:
      if their_external:
        message = (f"{self.their_name} has left the empathy.chat window "
                   "to continue the video/audio chat via an external client. "
                   "You should see/hear them again (shortly if not already), "
                   "but they may no longer see text messages sent via empathy.chat."
                  )
        Notification(message, timeout=None).show()
    self.their_external = their_external

  def update_their_complete(self, their_complete):
    if bool(their_complete) != self.their_complete:
      if their_complete:
        message = f"{self.their_name} has left this empathy chat."
        Notification(message, timeout=None).show()
    self.their_complete = their_complete
    
  def timer_2_tick(self, **event_args):
    """This method is called approx. once every 5 seconds, checking for messages"""
    if self._first_tick:
      self.lists_url = anvil.server.call('get_url', 'nycnvc_feelings_needs')
      if self.lists_card.visible:
        self.add_lists_pdf_viewer()
      self._first_tick = False
    self.update()

  def message_textbox_pressed_enter(self, **event_args):
    text = self.message_textbox.text
    if text:
      match_state = anvil.server.call('add_chat_message', message=text)
      self.message_textbox.text = ""
      self.update_messages(match_state['message_items'])
      #self.call_js('scrollCard')
      
  def complete_button_click(self, **event_args):
    self.timer_2.interval = 0
    if self.status == "matched":
      if self.jitsi_embed:
        self.jitsi_embed.visible = False
        window.japi.executeCommand('hangup')
      state = anvil.server.call('match_complete')
    else:
      state = anvil.server.call('cancel_now', self.proptime_id)
    ui.reload()
    #self.top_form.reset_status(state)   

  def slider_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    toggle_button_card(self.slider_button, self.slider_card)

  def hide_slider(self, **event_args):
    self.slider_card.visible = False
    self.slider_button.role = "raised"
    
  def timer_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    toggle_button_card(self.timer_button, self.timer_card)

  def my_timer_1_elapsed(self, **event_args):
    if not self.timer_card.visible:
      self.timer_button_click()
      
  def message_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    toggle_button_card(self.message_button, self.message_card)

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
      print(f"Handled: {repr(e)}")
    except ExternalError as e:
      Notification("Full screen toggle blocked by browser. Try F11.").show()
      self.full_screen_button.enabled = False
      print(f"Handled: {repr(e)}")

  def info_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    toggle_button_card(self.info_button, self.info_flow_panel)
    self._info_clicked = True

  def info_timer_tick(self, **event_args):
    """This method is called Every [interval] seconds. Does not trigger if [interval] is 0."""
    if not self._info_clicked and self.info_flow_panel.visible:
      self.info_button_click()

  def lists_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if not self.lists_card.visible:
      if self.lists_url:
        self.add_lists_pdf_viewer()
    elif self.lists_card.get_components():
      self.pdf_viewer.remove_from_parent()
    toggle_button_card(self.lists_button, self.lists_card)

  def add_lists_pdf_viewer(self):
    self.pdf_viewer = pdf_viewer(url=self.lists_url)
    self.lists_card.add_component(self.pdf_viewer)  
    
  def jitsi_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    if self.jitsi_embed:
      anvil.server.call('update_my_external', True)
      self.jitsi_embed.remove_from_parent()
      self.jitsi_embed = None
      window.japi.executeCommand('hangup')
    self.restore_button.visible = True
    
  def restore_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.restore_button.visible = False
    self.add_jitsi_embed()
    anvil.server.call('update_my_external', False)


def toggle_button_card(button, card):
  card.visible = not card.visible
  button.role = None if card.visible else "raised"