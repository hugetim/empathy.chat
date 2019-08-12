from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.google.auth, anvil.google.drive
import anvil.server
import anvil.users
from TimerForm import TimerForm
from MyJitsi import MyJitsi
import parameters as p
import anvil.tz
import helper as h
import random
import datetime


class MatchForm(MatchFormTemplate):
  tallies = dict(receive_first = 0,
                 will_offer_first = 0,
                 request_em = 0)
  status = None
  last_confirmed = None # this or other_last_confirmed, whichever is earlier
  ping_start = None
  request_em_hours = None
  request_em_set_time = None
  pause_hours_update = False
  jitsi_embed = None
  last_5sec = None
  seconds_left = None

  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)

    # 'prune' initializes new users to trust level 0 (via '_get_user_info')
    self.confirming_wait = False
    self.drop_down_1.items = (("Willing to offer empathy first","will_offer_first"),
                              ("Not ready to offer empathy first","receive_first"))
    tm, re, re_opts, re_st, pe, rt, s, lc, ps, tallies, e, n = anvil.server.call('init')
    if e == False:
      alert('This account is not yet authorized to match with other users. '
            + 'Instead, it can be used to test things out. Your actions will not impact '
            + 'or be visible to other users. '
            + 'For help, contact: ' + p.CONTACT_EMAIL)
    elif e == True:
      alert("Welcome, " + n + "!")
    elif n:
      self.welcome_label.text = "Hi, " + n + "!"
    self.test_mode.visible = tm
    self.init_request_em_opts(re, re_opts, re_st)
    self.pinged_em_check_box.checked = pe
    self.tallies = tallies
    self.drop_down_1.selected_value = rt
    self.jitsi_embed = None
    self.set_test_link()
    self.set_seconds_left(s, lc, ps)
    self.reset_status()

  def set_seconds_left(self, new_status=None, last_confirmed=None, ping_start=None):
    """
    Set status and related time variables
    """
    self.last_5sec = h.now()
    if (new_status and new_status != "matched"):
      self.seconds_left = h.seconds_left(new_status, last_confirmed, ping_start)
      if self.status == "pinging" and new_status == "requesting":
        self.seconds_left = max(self.seconds_left, p.BUFFER_SECONDS)
    self.status = new_status
    self.last_confirmed = last_confirmed
    self.ping_start = ping_start
    
  def request_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    request_type = self.drop_down_1.selected_value
    s, lc, ps, num_emailed = anvil.server.call('add_request', request_type)
    self.set_seconds_left(s, lc, ps)
    self.reset_status()
    if self.status == "requesting" and num_emailed > 0:
      self.emailed_notification(num_emailed).show()

  def emailed_notification(self, num):
    """assumes num>0, returns Notification"""
    if num == 1:
      message = ('Someone has been sent a '
                 + 'notification email about your request.')
      headline = 'Email notification sent'
    else:
      message = (str(num) + ' others have been sent '
                 + 'notification emails about your request.')
      headline = 'Email notifications sent'
    return Notification(message,
                        title=headline,
                        timeout=10)

  def renew_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.confirm_wait()

  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.set_seconds_left(None)
    self.tallies = anvil.server.call('cancel')
    self.reset_status()

  def complete_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.set_seconds_left(None)
    self.tallies = anvil.server.call('match_complete')
    self.reset_status()

  def timer_1_tick(self, **event_args):
    """This method is called once per second, updating timers"""
    if self.status == "requesting" and self.seconds_left > 0:
      self.seconds_left -= 1
      self.timer_label.text = ("Your request will expire in:  "
                               + h.seconds_to_digital(self.seconds_left) )
    elif self.status == "pinging" and self.seconds_left > 0:
      self.seconds_left -= 1
      self.status_label.text = ("Potential match available. Time left for them "
                                + "to confirm:  "
                                + h.seconds_to_digital(self.seconds_left))

  def timer_2_tick(self, **event_args):
    """This method is called approx. once per second, checking for status changes"""
    # Run this code approx. once a second
    if self.status == "requesting":
      if self.seconds_left <= 0:
        self.tallies = anvil.server.call('cancel')
        alert("Request cancelled due to "
              + h.seconds_to_words(p.WAIT_SECONDS) + " of inactivity.",
              dismissible=False)
        self.set_seconds_left(None)
        self.reset_status()
    elif self.status == "pinging" and self.seconds_left <= 0:
      s, lc, ps, self.tallies = anvil.server.call('cancel_other')
      self.set_seconds_left(s, lc, ps)
      self.reset_status()
    if (h.now() - self.last_5sec).seconds > 4.5:
      # Run this code every 5 seconds
      self.last_5sec = h.now()
      if (self.request_em_check_box.checked and self.re_radio_button_fixed.selected
          and self.pause_hours_update == False):
        hours_left = h.re_hours(self.request_em_hours, 
                                self.request_em_set_time)
        if hours_left <= 0:
          checked = False
          self.request_em_check_box.checked = checked
          self.set_request_em_options(checked)
          self.text_box_hours.text = "{:.1f}".format(self.request_em_hours)
          s, lc, ps, t, re_st = anvil.server.call('set_request_em', checked)
          self.request_em_set_time = re_st
          if s != self.status:
            self.set_seconds_left(s, lc, ps)
          self.tallies = t
          self.reset_status()
        else:
          self.text_box_hours.text = "{:.1f}".format(hours_left)
      if self.status == "requesting":
        s, lc, ps, self.tallies = anvil.server.call_s('get_status')
        if s != self.status:
          self.set_seconds_left(s, lc, ps)
          self.reset_status()
      elif self.status == "pinging":
        s, lc, ps, self.tallies = anvil.server.call_s('get_status')
        if self.status != "pinging":
          self.set_seconds_left(s, lc, ps)
          if self.status == "requesting":
            alert("The other empathy request was cancelled.")
          self.reset_status()
      elif self.status is None:
        self.tallies = anvil.server.call_s('get_tallies')
        self.update_tally_label()
      elif self.status == "matched":
        self.chat_repeating_panel.items = anvil.server.call_s('get_messages')
        self.call_js('scrollCard') 
        
  def confirm_wait(self):
    s, lc, ps, self.tallies = anvil.server.call('confirm_wait')
    self.set_seconds_left(s, lc, ps)
    self.reset_status()

  def confirm_match(self, seconds):
    if self.pinged_em_check_box.checked:
      anvil.server.call('pinged_email')
    f = TimerForm(seconds, self.status)
    out = alert(content=f,
                title="A match is available. Are you ready?",
                large=False,
                dismissible=False,
                buttons=[("Yes", True), ("No", False)])
    if out == True:
      self.status = "matched"
      s, lc, ps, self.tallies = anvil.server.call('match_commenced')
      self.set_seconds_left(s, lc, ps)
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
      print (out)
      assert out == "requesting"
      s, lc, ps, self.tallies = anvil.server.call_s('get_status')
      self.set_seconds_left(s, lc, ps)
    self.reset_status()

  def reset_status(self):
    """
    Update form according to current state variables
    """
    if self.status:
      self.welcome_label.visible = False
      self.request_button.visible = False
      self.drop_down_1.enabled = False
      self.drop_down_1.foreground = "gray"
      self.tally_label.visible = False
      if self.status == "requesting":
        self.status_label.text = "Status: Requesting an empathy exchange."
        self.note_label.text = ("(Note: When a match becomes available, "
                                + "you will have "
                                + h.seconds_to_words(p.CONFIRM_MATCH_SECONDS)
                                + " to confirm the match.)")
        self.note_label.visible = True
        self.status_label.bold = False
        self.set_jitsi_link("")
        self.timer_label.text = ("Your request will expire in:  "
                                 + h.seconds_to_digital(self.seconds_left) )
        self.timer_label.visible = True
        self.complete_button.visible = False
        self.renew_button.visible = True
        self.cancel_button.visible = True
        self.pinged_em_check_box.visible = True
      else:
        if self.status == "pinged":
          return self.confirm_match(self.seconds_left)
        assert self.status in ["pinging", "matched"]
        if self.status == "pinging":
          self.status_label.text = ("Potential match available. Time left for them "
                                    + "to confirm:  "
                                    + h.seconds_to_digital(self.seconds_left))
          self.set_jitsi_link("")
          self.timer_label.visible = False
          self.note_label.visible = False
          self.status_label.bold = False
          self.renew_button.visible = False
          self.cancel_button.visible = True
          self.complete_button.visible = False
        else:
          assert self.status == "matched"
          self.timer_label.visible = False
          jitsi_code, request_type = anvil.server.call('get_code')
          self.status_label.text = "Status: Exchanging Empathy"
          self.status_label.bold = False
          self.renew_button.visible = False
          self.cancel_button.visible = False
          self.complete_button.visible = True
          self.set_jitsi_link(jitsi_code)
          self.note_label.text = "Note: If video does not appear above, try clicking the link below or using the Jitsi Meet app."
          self.note_label.visible = True
        self.pinged_em_check_box.visible = False
    else:
      self.welcome_label.visible = True
      self.status_label.text = "Request an empathy match whenever you're ready."
      self.status_label.bold = False
      self.set_jitsi_link("")
      self.note_label.text = ""
      self.note_label.visible = False
      self.timer_label.visible = False
      self.complete_button.visible = False
      self.renew_button.visible = False
      self.cancel_button.visible = False
      self.request_button.visible = True
      self.drop_down_1.enabled = True
      self.drop_down_1.foreground = "black"
      self.pinged_em_check_box.visible = False
      self.update_tally_label()

  def update_tally_label(self):
    temp = ""
    if self.tallies['receive_first'] > 1:
      if self.tallies['will_offer_first'] > 0:
        temp = ('There are currently '
                + str(self.tallies['receive_first'] + self.tallies['will_offer_first'])
                + ' others requesting an empathy exchange. Some are '
                + 'requesting a match with someone willing to offer empathy first.')
      else:
        assert self.tallies['will_offer_first'] == 0
        temp = ('There are currently '
                + str(self.tallies['receive_first'])
                + ' others requesting matches with someone willing to offer empathy first.')
    elif self.tallies['receive_first'] == 1:
      if self.tallies['will_offer_first'] > 0:
        temp = ('There are currently '
                + str(self.tallies['receive_first'] + self.tallies['will_offer_first'])
                + ' others requesting an empathy exchange. '
                + 'One is requesting a match with someone willing to offer empathy first.')
      else:
        assert self.tallies['will_offer_first'] == 0
        temp = ('There is currently one person requesting a match with someone willing to offer empathy first.')
    else:
      assert self.tallies['receive_first'] == 0
      if self.tallies['will_offer_first'] > 1:
        temp = ('There are currently '
                + str(self.tallies['will_offer_first'])
                + ' others requesting an empathy exchange, '
                + 'all of whom are willing to offer empathy first.')
      elif self.tallies['will_offer_first'] == 1:
        temp = ('There is currently '
                + str(self.tallies['will_offer_first'])
                + ' person requesting an empathy exchange, '
                + 'willing to offer empathy first.')
      else:
        assert self.tallies['will_offer_first'] == 0
    if self.tallies['will_offer_first'] == 0:
      if self.tallies['receive_first'] > 0:
        if self.tallies['request_em'] > 1:
          temp += (str(self.tallies['request_em'])
                   + ' others are currently receiving email notifications '
                   + 'about each request for empathy.')
        elif self.tallies['request_em'] == 1:
          temp += (str(self.tallies['request_em'])
                   + ' other person is currently receiving email notifications '
                   + 'about each request for empathy.')
        self.tally_label.font_size = None
      else:
        self.tally_label.font_size = 12
        if self.tallies['request_em'] > 1:
          temp += (str(self.tallies['request_em'])
                   + ' people are currently receiving email notifications '
                   + 'about each request for empathy.')
        elif self.tallies['request_em'] == 1:
          temp += (str(self.tallies['request_em'])
                   + ' person is currently receiving email notifications '
                   + 'about each request for empathy.')
    else:
      self.tally_label.font_size = None
    self.tally_label.text = temp
    if len(temp) > 0:
      self.tally_label.visible = True
    else:
      self.tally_label.visible = False

  def set_jitsi_link(self, jitsi_code):
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

  def set_test_link(self):
    num_chars = 4
    charset = "abcdefghijkmnopqrstuvwxyz23456789"
    random.seed()
    rand_code = "".join([random.choice(charset) for i in range(num_chars)])
    code = "test-" + rand_code
    self.test_link.url = "https://meet.jit.si/" + code
    return code      
      
  def logout_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.logout_user()

  def link_bar_logout_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.logout_user()
    
  def logout_user(self):
    anvil.users.logout()
    self.set_seconds_left(None)
    self.reset_status()
    open_form('LoginForm')

  def pinged_em_check_box_change(self, **event_args):
    """This method is called when this checkbox is checked or unchecked"""
    checked = self.pinged_em_check_box.checked
    s, lc, ps, t = anvil.server.call('set_pinged_em', checked)
    self.set_seconds_left(s, lc, ps)
    self.tallies = t
    self.reset_status()

  def request_em_check_box_change(self, **event_args):
    """This method is called when this checkbox is checked or unchecked"""
    checked = self.request_em_check_box.checked
    self.set_request_em_options(checked)
    s, lc, ps, t, re_st = anvil.server.call('set_request_em', checked)
    self.request_em_set_time = re_st
    self.set_seconds_left(s, lc, ps)
    self.tallies = t
    self.reset_status()

  def set_request_em_options(self, checked):
    """Update state of request_em options."""
    if checked:
      self.re_radio_button_panel.visible = True
      self.re_radio_button_indef.enabled = True
      self.re_radio_button_fixed.enabled = True
      self.text_box_hours.enabled = self.re_radio_button_fixed.selected
    else:
      self.re_radio_button_panel.visible = False
      self.re_radio_button_indef.enabled = False
      self.re_radio_button_fixed.enabled = False
      self.text_box_hours.enabled = False

  def init_request_em_opts(self, re, re_opts, re_st):
    """Initialize to saved request_em option values"""
    self.request_em_check_box.checked = re
    self.request_em_hours = re_opts["hours"]
    self.request_em_set_time = re_st
    fixed = bool(re_opts["fixed"])
    self.re_radio_button_indef.selected = not fixed
    self.re_radio_button_fixed.selected = fixed
    if self.request_em_check_box.checked and fixed:
      hours_left = h.re_hours(self.request_em_hours, 
                              self.request_em_set_time)
    else:
      hours_left = self.request_em_hours
    self.set_request_em_options(re)
    self.text_box_hours.text = "{:.1f}".format(hours_left)

  def re_radio_button_indef_clicked(self, **event_args):
    """This method is called when this radio button is selected"""
    fixed = False
    self.text_box_hours.enabled = fixed
    hours = self.text_box_hours.text
    self.request_em_hours = hours
    s, lc, ps, t, re_st = anvil.server.call('set_request_em_opts', fixed, hours)
    self.request_em_set_time = re_st
    self.set_seconds_left(s, lc, ps)
    self.tallies = t
    self.reset_status() 
    
  def re_radio_button_fixed_clicked(self, **event_args):
    """This method is called when this radio button is selected"""
    fixed = True
    self.text_box_hours.enabled = fixed
    hours = self.text_box_hours.text
    self.request_em_hours = hours
    s, lc, ps, t, re_st = anvil.server.call('set_request_em_opts', fixed, hours)
    self.request_em_set_time = re_st
    self.set_seconds_left(s, lc, ps)
    self.tallies = t
    self.reset_status() 

  def text_box_hours_pressed_enter(self, **event_args):
    """This method is called when the user presses Enter in this text box"""
    self.update_hours()

  def text_box_hours_lost_focus(self, **event_args):
    """This method is called when the TextBox loses focus"""
    self.update_hours()
    self.pause_hours_update = False
  
  def update_hours(self):
    hours = self.text_box_hours.text
    if hours and hours > 0:
      fixed = self.re_radio_button_fixed.selected
      self.request_em_hours = hours
      s, lc, ps, t, re_st = anvil.server.call('set_request_em_opts', fixed, hours)
      self.request_em_set_time = re_st
      self.set_seconds_left(s, lc, ps)
      self.tallies = t
      self.reset_status()
    else:
      hours_left = h.re_hours(self.request_em_hours, 
                              self.request_em_set_time)
      self.text_box_hours.text = "{:.1f}".format(hours_left)

  def text_box_hours_focus(self, **event_args):
    """This method is called when the TextBox gets focus"""
    self.pause_hours_update = True   

  def message_textbox_pressed_enter(self, **event_args):
    """This method is called when the user presses Enter in this text box"""
    anvil.server.call('add_message', self.message_textbox.text)
    self.message_textbox.text = ""
    self.chat_repeating_panel.items = anvil.server.call('get_messages')
    self.call_js('scrollCard')
    
  def test_mode_change(self, **event_args):
    """This method is called when this checkbox is checked or unchecked"""
    self.test_column_panel.visible = self.test_mode.checked
    if self.test_mode.checked:
      self.test_requestuser_drop_down_refresh()

  def test_adduser_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    email = self.test_adduser_email.text
    if email:
      anvil.server.call('test_add_user', email)
      self.test_adduser_email.text = ""
      self.test_requestuser_drop_down_refresh()
    else:
      alert("Email address required to add user.")

  def test_request_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    user_id = self.test_requestuser_drop_down.selected_value
    requesttype = self.test_requesttype_drop_down.selected_value
    if user_id and requesttype:
      anvil.server.call('test_add_request', user_id, requesttype)
    else:
      alert("User and request type required to add request.")

  def test_clear_click(self, **event_args):
    """This method is called when the button is clicked"""
    anvil.server.call('test_clear')
    self.test_requestuser_drop_down_refresh()

  def test_requestuser_drop_down_refresh(self):
    out = anvil.server.call('test_get_user_list')
    self.test_requestuser_drop_down.items = out

  def test_other_action_click(self, **event_args):
    """This method is called when the button is clicked"""
    action = self.test_other_action_drop_down.selected_value
    user_id = self.test_requestuser_drop_down.selected_value
    anvil.server.call(action, user_id)
