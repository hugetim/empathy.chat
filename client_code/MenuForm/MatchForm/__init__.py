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
from ... import exchange_controller as ec
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
    self.lists_url = ""
    self._info_clicked = False
    self.info_button.role = ""

  def form_show(self, **event_args):
    """This method is called when the HTML panel is shown on the screen"""
    self.item = ec.init_pending_exchange(self.item['status'])
    self.my_timer_1.minutes = self.item.default_timer_minutes
    self.set_jitsi_link()
    self.chat_repeating_panel.items = []
    self.init_slider_panel()
    self.base_status_reset()
    self.first_update = True
    self.update()
    if glob.MOBILE:
      alert(content=MobileAlert(), title="Attention mobile users", large=True)
    self._first_tick = True
    self.timer_2.interval = 5

  def set_jitsi_link(self):
    """Initialize or destroy embedded Jitsi Meet instance"""
    self.jitsi_link.url = self.item.jitsi_url
    self.jitsi_link.text = "" #jitsi_code
    self.jitsi_code = self.item.jitsi_code
    self.jitsi_link.visible = True
    self.add_jitsi_embed()
    self.jitsi_column_panel.visible = True
    
  def add_jitsi_embed(self):
    if not self.jitsi_embed:
      self.jitsi_embed = MyJitsi(item={'room_name': self.jitsi_code, 'name': glob.name, 'domain': self.item.jitsi_domain})
      self.jitsi_column_panel.add_component(self.jitsi_embed)
 
  def jitsi_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    if self.jitsi_embed:
      ec.update_my_external(True)
      self.jitsi_embed.remove_from_parent()
      self.jitsi_embed = None
      window.japi.executeCommand('hangup')
    self.restore_button.visible = True
    
  def restore_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.restore_button.visible = False
    self.add_jitsi_embed()
    ec.update_my_external(False) 
      
  def complete_button_click(self, **event_args):
    self.timer_2.interval = 0
    if self.item.status == "matched":
      if self.jitsi_embed:
        self.jitsi_embed.visible = False
        window.japi.executeCommand('hangup')
    self.item.exit()
    ui.reload()  
    
  def init_slider_panel(self):
    my_value = 5 if ec.slider_value_missing(self.item.my_slider_value) else self.item.my_slider_value
    slider_item = {'visible': True, 'status': self.item.slider_status, 
                   'my_value': my_value, 'their_value': 5, 'their_name': ""}
    self.slider_button_click()
    self.slider_panel = SliderPanel(item=slider_item)
    self.slider_column_panel.add_component(self.slider_panel)
    self.slider_panel.set_event_handler('x-hide', self.hide_slider)
    
  def update(self):
    previous_status = self.item.status
    previous_slider_status = self.item.slider_status
    previous_their_external = self.item.their_external
    previous_their_complete = self.item.their_complete
    self.item = ec.update_exchange_state(self.item)
    self.update_status(prev=previous_status)
    self.slider_panel.update_name(self.item.their_name)
    if previous_slider_status != self.item.slider_status:
      if self.item.slider_status == "received":
        self.slider_panel.receive_value(self.item.their_slider_value)
      else:
        self.slider_panel.update_status(self.item.slider_status)
    self.update_messages()
    self.update_their_external(prev_their_external=previous_their_external)
    self.update_their_complete(prev_their_complete=previous_their_complete)

  def base_status_reset(self):
      if not self.item.status:
        return ui.reload()
      matched = self.item.status == "matched"
      self.message_textbox.enabled = matched
      self.message_textbox.tooltip = (
        "" if matched else "Please wait until the other has joined before sending a message"
      )
      self.complete_button.visible = True
      self.complete_button.text = "End Chat" if matched else "Cancel"
      self.status_label.visible = self.item.status == "requesting"
    
  def update_status(self, prev):
    if prev != self.item.status:
      self.base_status_reset()
      if self.item.status == "matched":
        ec.update_my_external(not bool(self.jitsi_embed))
      if self.item.status == "pinged":
        self.pinged()

  def pinged(self):
    with h.PausedTimer(self.timer_2):
      self._play_sound('doorbell')
      if self.jitsi_embed:
        with ui.BrowserTab("Someone waiting to join your empathy.chat", "_/theme/favicon-dot.ico"):
          ready = confirm("Someone has asked to join your empathy chat. Are you still available to exchange empathy?")
      else: # User has popped out video and so may not see confirm dialog
        ready = True
      self.process_pinged_response(ready)
      
  def process_pinged_response(self, ready):
    if ready:
      this_status = self.item.status
      self.item.start_exchange()
      self.update_status(prev=this_status)
    else:
      self.item.exit()
      ui.reload()

  def update_messages(self):
    old_items = self.chat_repeating_panel.items
    messages_plus = self.item.messages_plus
    if len(messages_plus) > len(old_items):
      self.chat_repeating_panel.items = messages_plus
      self.message_card.visible = True
      self.message_button.role = None
      self.call_js('scrollCard')
      if not self.first_update:
        self.chat_display_card.scroll_into_view()
      self.first_update = False
  
  def update_their_external(self, prev_their_external):
    if bool(prev_their_external) != bool(self.item.their_external):
      if self.item.their_external:
        message = (f"{self.item.their_name} has left the empathy.chat window "
                   'to continue the video/audio chat in a separate, "popped-out" window. '
                   "You should see/hear them again shortly (if not already)."
                  )
        Notification(message, timeout=None).show()

  def update_their_complete(self, prev_their_complete):
    if bool(prev_their_complete) != bool(self.item.their_complete):
      if self.item.their_complete:
        message = f"{self.item.their_name} has left this empathy chat."
        Notification(message, timeout=None).show()
    
  def timer_2_tick(self, **event_args):
    """This method is called approx. once every 5 seconds, checking for messages"""
    if self._first_tick:
      [self.lists_url, *clip_urls] = ec.get_urls()
      self.call_js('loadClips', *clip_urls)
      if self.lists_card.visible:
        self.add_lists_pdf_viewer()
      self._first_tick = False
    self.update()

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
    self._play_sound('ding')
    if not self.timer_card.visible:
      self.timer_button_click()

  def _play_sound(self, audio_id):
    try:
      self.call_js('playSound', audio_id)
    except ExternalError as err:
      print(f"Error playing {audio_id} sound: {repr(err)}")        
              
  def message_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    toggle_button_card(self.message_button, self.message_card)
    
  def message_textbox_pressed_enter(self, **event_args):
    text = self.message_textbox.text
    if text:
      self.item.add_chat_message(text)
      self.message_textbox.text = ""
      self.update_messages()

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

      
def toggle_button_card(button, card):
  card.visible = not card.visible
  button.role = None if card.visible else "raised"