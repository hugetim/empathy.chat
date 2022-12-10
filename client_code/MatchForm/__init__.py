from ._anvil_designer import MatchFormTemplate
from anvil import *
from anvil.js import window, ExternalError
from pdf_viewer.pdf_viewer import pdf_viewer
from .. import ui_procedures as ui
from .. import glob
from .. import helper as h
from .. import exchange_controller as ec
from .MyJitsi import MyJitsi
from .SliderPanel import SliderPanel
from .MobileAlert import MobileAlert


class MatchForm(MatchFormTemplate):
  state_keys = {'status'}
  
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
    #
    self.jitsi_embed = None
    self.lists_url = ""
    self.first_messages_update = True
    self._doorbell_muted = glob.APPLE
    self._clips_loaded = False
    self._update_doorbell_link()
    self.init_subscriptions()
    self._initialized_sounds = set()

  def form_show(self, **event_args):
    """This method is called when the HTML panel is shown on the screen"""
    self.initial_form_setup()
    if glob.MOBILE:
      alert(content=MobileAlert(), title="Attention mobile users", large=True)
    self.timer_2.interval = 5
    if not self.lists_url:
      self.load_lists_and_sounds()

  def initial_form_setup(self):
    self.item = ec.ExchangeState.initialized_state(self.item['status'])
    self.my_timer_1.minutes = self.item.default_timer_minutes
    self.init_jitsi()
    self.init_slider_panel()
    self.base_status_reset() # to initialize some visible things before update server call delay
    self.item.update()
  
  def init_jitsi(self):
    """Initialize or destroy embedded Jitsi Meet instance"""
    self.add_jitsi_embed()
    self.jitsi_column_panel.visible = True
    self.jitsi_link.url = self.item.jitsi_url
    self.jitsi_link.visible = True
    
  def add_jitsi_embed(self):
    if not self.jitsi_embed:
      self.jitsi_embed = MyJitsi(item={'room_name': self.item.jitsi_code, 'name': glob.name, 'domain': self.item.jitsi_domain})
      self.jitsi_column_panel.add_component(self.jitsi_embed)

  def remove_jitsi_embed(self):
    self.jitsi_embed.remove_from_parent()
    self.jitsi_embed = None 

  def hide_and_hangup_jitsi_embed(self):
    self.jitsi_embed.visible = False
    window.japi.executeCommand('hangup')
  
  def jitsi_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    if self.jitsi_embed:
      self.hide_and_hangup_jitsi_embed()
      ec.update_my_external(True)
      self.remove_jitsi_embed()
      self.restore_button.visible = True
    
  def restore_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.restore_button.visible = False
    self.add_jitsi_embed()
    ec.update_my_external(False) 
      
  def complete_button_click(self, **event_args):
    with h.PausedTimer(self.timer_2), h.Disabled(self.complete_button):
      if self.jitsi_embed:
        self.hide_and_hangup_jitsi_embed()
      self.item.exit()
      ui.init_load()  
    
  def init_slider_panel(self):
    slider_item = {'their_name': "", 'status': self.item.slider_status, 
                   'my_value': self.item.my_initial_slider_value(), 'their_value': 5}
    self.slider_panel = SliderPanel(item=slider_item)
    self.slider_column_panel.add_component(self.slider_panel)
    self.slider_panel.set_event_handler('x-hide', self.slider_button_click)
    self.slider_button_click()

  def update_slider_panel(self, dispatch=None):
    self.slider_panel.update_name(self.item.their_name)
    if self.item.slider_status == "received":
      self.slider_panel.receive_value(self.item.their_slider_value)
    else:
      self.slider_panel.update_status(self.item.slider_status)

  def init_subscriptions(self):
    glob.publisher.subscribe("match.status", self, self.update_status)
    glob.publisher.subscribe("match.slider", self, self.update_slider_panel)
    glob.publisher.subscribe("match.messages", self, self.update_messages)
    glob.publisher.subscribe("match.external", self, self.update_their_external)
    glob.publisher.subscribe("match.complete", self, self.update_their_complete)
    glob.publisher.subscribe("match.update_how", self, self.update_how_empathy_items)
  
  def base_status_reset(self):
    if not self.item.status:
      return ui.init_load()
    self.status_label.visible = self.item.status == "requesting"
    self._update_doorbell_visible()
    matched = self.item.status == "matched"
    self.message_textbox.enabled = matched
    self.message_textbox.tooltip = (
      "" if matched else "You will be able to send a message once someone else has joined"
    )
    self.complete_button.text = "End Chat" if matched else "Cancel"
    self.complete_button.visible = True

  def update_how_empathy_items(self, dispatch=None):
    how_empathy_items = self.item.how_empathy_items
    if how_empathy_items:
      self.how_empathy_drop_down.items = how_empathy_items
      self.update_how_empathy_label()
      self.info_button.visible = True
      if how_empathy_items[0][1]: # whether they have how_empathy
        if not self.info_flow_panel.visible:
          self.info_button_click()
  
  def update_status(self, dispatch=None):
    self.base_status_reset()
    if self.item.status == "matched":
      ec.update_my_external(not bool(self.jitsi_embed))
    if self.item.status == "pinged":
      self.pinged()

  def pinged(self):
    with h.PausedTimer(self.timer_2):
      if not self._doorbell_muted:
        self._play_sound('doorbell')
      if self.jitsi_embed:
        with ui.BrowserTab("Someone waiting to join your empathy.chat", "_/theme/favicon-dot.ico"):
          ready = confirm("Someone has asked to join your empathy chat. Are you still available to exchange empathy?")
      else: # User has popped out video and so may not see confirm dialog
        ready = True
      self.process_pinged_response(ready)
      
  def process_pinged_response(self, ready):
    if ready:
      self.item.start_exchange()
      if self.item.status == "requesting":
        Notification("The user who had asked to join has now cancelled their request.", timeout=None, style="warning").show()
    else:
      self.item.exit()
      ui.init_load()

  def update_messages(self, dispatch=None):
    self.chat_repeating_panel.items = self.item.messages_plus
    self.put_new_messages_in_view()
    self.first_messages_update = False

  def put_new_messages_in_view(self):
    self.message_card.visible = True
    self.message_button.role = None
    self.call_js('scrollCard')
    if not self.first_messages_update:
      self.chat_display_card.scroll_into_view()
  
  def update_their_external(self, dispatch=None):
    if self.item.their_external:
      message = (f"{self.item.their_name} has left the empathy.chat window "
                  'to continue the video/audio chat in a separate, "popped-out" window. '
                  "You should see/hear them again shortly, if not already. "
                  "(Note: This means they may not see Text Chat messages you send from here--or likewise the Slider.)"
                )
      Notification(message, timeout=None).show()

  def update_their_complete(self, dispatch=None):
    if self.item.their_complete:
      message = f"{self.item.their_name} has left this empathy chat."
      Notification(message, timeout=None).show()
    
  def timer_2_tick(self, **event_args):
    """This method is called approx. once every 5 seconds, checking for messages"""
    self.item.update()

  def load_lists_and_sounds(self):
    [self.lists_url, *clip_urls] = ec.get_urls()
    self.call_js('loadClips', *clip_urls)
    self._clips_loaded = True
    self._update_doorbell_visible()
    if self.lists_card.visible:
      self.add_lists_pdf_viewer()

  def _update_doorbell_visible(self):
    self.mute_doorbell_link.visible = self.status_label.visible and self._clips_loaded

  def _update_doorbell_link(self):
    if self._doorbell_muted:
      self.mute_doorbell_link.icon = 'fa:bell-slash'
      self.mute_doorbell_link.text = "doorbell sound (upon arrival) muted"
    else:
      self.mute_doorbell_link.icon = 'fa:bell'
      self.mute_doorbell_link.text = "doorbell sound will play upon arrival"
  
  def mute_doorbell_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self._doorbell_muted = not self._doorbell_muted
    if 'doorbell' not in self._initialized_sounds:
      self._initialize_sound('doorbell')
    self._update_doorbell_link()

  def timer_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    toggle_button_card(self.timer_button, self.timer_card)

  def my_timer_1_started(self, **event_args):
    if 'ding' not in self._initialized_sounds:
      self._initialize_sound('ding')
  
  def my_timer_1_elapsed(self, **event_args):
    self._play_sound('ding')
    if not self.timer_card.visible:
      self.timer_button_click()

  def _initialize_sound(self, audio_id):
    self._initialized_sounds.add(audio_id)
    try:
      self.call_js('initSound', audio_id)
    except ExternalError as err:
      print(f"Error playing {audio_id} sound: {repr(err)}")    
  
  def _play_sound(self, audio_id):
    try:
      self.call_js('playSound', audio_id)
    except ExternalError as err:
      print(f"Error playing {audio_id} sound: {repr(err)}")        
              
  def message_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    toggle_button_card(self.message_button, self.message_card)
    
  def message_textbox_pressed_enter(self, **event_args):
    message_text = self.message_textbox.text
    if message_text:
      self.item.add_chat_message(message_text)
      self.message_textbox.text = ""
      self.chat_repeating_panel.items = self.item.messages_plus

  def slider_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    toggle_button_card(self.slider_button, self.slider_card)
  
  def lists_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    # Complications are necessitated by vaguaries of pdf_viewer loading
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
      self.manage_full_screen_error(e)
    except ExternalError as e:
      self.manage_full_screen_error(e)

  def manage_full_screen_error(self, e):
    Notification("Full screen toggle blocked by browser. Try F11.").show()
    self.full_screen_button.enabled = False
    print(f"Handled: {repr(e)}")
  
  def info_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    toggle_button_card(self.info_button, self.info_flow_panel)

  def update_how_empathy_label(self, **event_args):
    """This method is called when an item is selected"""
    how_empathy = self.how_empathy_drop_down.selected_value
    self.how_empathy_label.text = how_empathy


def toggle_button_card(button, card):
  card.visible = not card.visible
  button.role = None if card.visible else "raised"
