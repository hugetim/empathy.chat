from ._anvil_designer import MenuFormTemplate
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


class MenuForm(MenuFormTemplate):
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
  
    # 'prune' initializes new users to trust level 0 (via '_get_user_info')
    self.confirming_wait = False
    self.drop_down_1_items = (("Willing to offer empathy first","will_offer_first"),
                              ("Not ready to offer empathy first","receive_first"))
    tm, re, re_opts, re_st, pe, rt, s, sl, tallies, e, n = anvil.server.call('init')
    if e == False:
      alert('This account is not yet authorized to match with other users. '
            + 'Instead, it can be used to test things out. Your actions will not impact '
            + 'or be visible to other users. '
            + 'For help, contact: ' + p.CONTACT_EMAIL,
            dismissible=False)
    elif e == True:
      alert("Welcome, " + n + "!")
    self.name = n
    self.test_mode.visible = tm
    self.init_request_em_opts(re, re_opts, re_st)
    self.pinged_em_check_box.checked = pe
    self.tallies = tallies
    self.request_type = rt
    self.set_test_link()
    self.set_seconds_left(s, sl)
    self.reset_status()
    self.timer_2.interval = 1
    
  def set_seconds_left(self, new_status=None, new_seconds_left=None):
    """Set status and related time variables"""
    self.last_5sec = h.now()
    if new_status and new_status != "matched":
      self.seconds_left = new_seconds_left
      if self.status == "pinging" and new_status == "requesting":
        self.seconds_left = max(self.seconds_left, p.BUFFER_SECONDS)
    #print('before status change: ', self.seconds_left)
    self.status = new_status

  def request_button_click(request_type):
    self.request_type = request_type
    s, sl, num_emailed = anvil.server.call('add_request', self.request_type)
    self.set_seconds_left(s, sl)
    self.reset_status()
    if self.status == "requesting" and num_emailed > 0:
      self.emailed_notification(num_emailed).show()
    
  def emailed_notification(self, num):
    """Return Notification (assumes num>0)"""
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
    self.confirm_wait()

  def cancel_button_click(self, **event_args):
    self.set_seconds_left(None)
    self.tallies = anvil.server.call('cancel')
    self.reset_status()

  def complete_button_click(self, **event_args):
    self.set_seconds_left(None)
    self.tallies = anvil.server.call('match_complete')
    self.reset_status()

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
      s, sl, self.tallies = anvil.server.call('cancel_other')
      self.set_seconds_left(s, sl)
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
          s, sl, t, re_st = anvil.server.call_s('set_request_em', checked)
          self.request_em_set_time = re_st
          if s != self.status:
            self.set_seconds_left(s, sl)
            self.reset_status()
          if not s:
            self.tallies = t
            self.update_tally_label()
        else:
          self.text_box_hours.text = "{:.1f}".format(hours_left)
      if self.status == "requesting":
        s, sl, self.tallies = anvil.server.call_s('get_status')
        if s != self.status:
          self.set_seconds_left(s, sl)
          self.reset_status()
      elif self.status == "pinging":
        s, sl, self.tallies = anvil.server.call_s('get_status')
        if s != self.status:
          self.set_seconds_left(s, sl)
          if self.status == "requesting":
            alert("The other empathy request was cancelled.")
          self.reset_status()
      elif self.status == "matched":
        old_items = self.chat_repeating_panel.items
        new_items = anvil.server.call_s('get_messages')
        if len(new_items) > len(old_items):
          self.chat_repeating_panel.items = new_items
          self.call_js('scrollCard')
          self.chat_display_card.scroll_into_view()
        
  def confirm_wait(self):
    s, sl, self.tallies = anvil.server.call('confirm_wait')
    self.set_seconds_left(s, sl)
    self.reset_status()

  def reset_status(self):
    """Update form according to current state variables"""
    if self.status:
      self.drop_down_1.enabled = False
      self.drop_down_1.foreground = "gray"
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
        self.pinged_em_check_panel.visible = True
      else:
        if self.status == "pinged":
          return self.confirm_match(self.seconds_left)
        assert self.status in ["pinging", "matched"]
        if self.status == "pinging":
          self.status_label.text = ("A potential match is available. They have "
                                    + "this long to confirm they are ready:  "
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
          self.note_label.text = "Note: If video does not appear above, try clicking the link below."
          self.note_label.visible = True
        self.pinged_em_check_panel.visible = False
    else:
      self.content = DashForm(self.name,
                                  self.drop_down_1_items, 
                                  self.request_type, 
                                  self.tallies)
      self.add_component(self.content)

  def set_test_link(self):
    num_chars = 4
    charset = "abcdefghijkmnopqrstuvwxyz23456789"
    random.seed()
    rand_code = "".join([random.choice(charset) for i in range(num_chars)])
    code = "test-" + rand_code
    self.test_link.url = "https://meet.jit.si/" + code
    return code      
      
  def logout_button_click(self, **event_args):
    self.logout_user()

  def link_bar_logout_click(self, **event_args):
    self.logout_user()
    
  def logout_user(self):
    anvil.users.logout()
    open_form('LoginForm')

  def request_em_check_box_change(self, **event_args):
    """This method is called when this checkbox is checked or unchecked"""
    checked = self.request_em_check_box.checked
    self.set_request_em_options(checked)
    s, sl, t, re_st = anvil.server.call('set_request_em', checked)
    self.request_em_set_time = re_st
    self.set_seconds_left(s, sl)
    self.tallies = t
    self.reset_status()

  def set_request_em_options(self, checked):
    """Update request_em options visibility/enabled."""
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
    fixed = False
    self.text_box_hours.enabled = fixed
    hours = self.text_box_hours.text
    self.request_em_hours = hours
    s, sl, t, re_st = anvil.server.call('set_request_em_opts', fixed, hours)
    self.request_em_set_time = re_st
    self.set_seconds_left(s, sl)
    self.tallies = t
    self.reset_status() 
    
  def re_radio_button_fixed_clicked(self, **event_args):
    fixed = True
    self.text_box_hours.enabled = fixed
    hours = self.text_box_hours.text
    self.request_em_hours = hours
    s, sl, t, re_st = anvil.server.call('set_request_em_opts', fixed, hours)
    self.request_em_set_time = re_st
    self.set_seconds_left(s, sl)
    self.tallies = t
    self.reset_status() 

  def text_box_hours_pressed_enter(self, **event_args):
    self.update_hours()

  def text_box_hours_lost_focus(self, **event_args):
    self.update_hours()
    self.pause_hours_update = False
  
  def update_hours(self):
    hours = self.text_box_hours.text
    if hours and hours > 0:
      fixed = self.re_radio_button_fixed.selected
      self.request_em_hours = hours
      s, sl, t, re_st = anvil.server.call('set_request_em_opts', fixed, hours)
      self.request_em_set_time = re_st
      self.set_seconds_left(s, sl)
      self.tallies = t
      self.reset_status()
    else:
      hours_left = h.re_hours(self.request_em_hours, 
                              self.request_em_set_time)
      self.text_box_hours.text = "{:.1f}".format(hours_left)

  def text_box_hours_focus(self, **event_args):
    self.pause_hours_update = True
    
  def test_mode_change(self, **event_args):
    """This method is called when this checkbox is checked or unchecked"""
    self.test_column_panel.visible = self.test_mode.checked
    if self.test_mode.checked:
      self.test_requestuser_drop_down_refresh()

  def test_adduser_button_click(self, **event_args):
    email = self.test_adduser_email.text
    if email:
      anvil.server.call('test_add_user', email)
      self.test_adduser_email.text = ""
      self.test_requestuser_drop_down_refresh()
    else:
      alert("Email address required to add user.")

  def test_request_button_click(self, **event_args):
    user_id = self.test_requestuser_drop_down.selected_value
    requesttype = self.test_requesttype_drop_down.selected_value
    if user_id and requesttype:
      anvil.server.call('test_add_request', user_id, requesttype)
    else:
      alert("User and request type required to add request.")

  def test_clear_click(self, **event_args):
    anvil.server.call('test_clear')
    self.test_requestuser_drop_down_refresh()

  def test_requestuser_drop_down_refresh(self):
    out = anvil.server.call('test_get_user_list')
    self.test_requestuser_drop_down.items = out

  def test_other_action_click(self, **event_args):
    action = self.test_other_action_drop_down.selected_value
    user_id = self.test_requestuser_drop_down.selected_value
    anvil.server.call(action, user_id)
