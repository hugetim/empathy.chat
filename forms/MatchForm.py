from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.google.auth, anvil.google.drive
import anvil.server
import anvil.users
from TimerForm import TimerForm
import parameters as p
import anvil.tz
import helper as h


class MatchForm(MatchFormTemplate):
  tallies = dict(receive_first = 0,
                 will_offer_first = 0,
                 request_em = 0)
  status = None
  last_confirmed = None # this or other_last_confirmed, whichever is earlier
  ping_start = None

  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)

    # 'prune' initializes new users to trust level 0 (via '_get_user_info')
    self.confirming_wait = False
    self.drop_down_1.items = (("Willing to offer empathy first","will_offer_first"),
                              ("Not ready to offer empathy first","receive_first"))
    tm, re, pe, rt, s, lc, ps, tallies, e = anvil.server.call('prune')
    if e == False:
      alert('This account is not yet authorized to match with other users. '
            + 'You can test things out, but your actions will not impact '
            + 'or be visible to other users. '
            + 'For help, contact: ' + p.CONTACT_EMAIL)
    self.test_mode.visible = tm
    self.request_em_check_box.checked = re
    self.pinged_em_check_box.checked = pe
    self.tallies = tallies
    self.drop_down_1.selected_value = rt
    self.status = s
    self.last_confirmed = lc
    self.ping_start = ps
    self.reset_status()

  def seconds_left(self):
    """derive seconds_left from status, last_confirmed, and ping_start"""
    return h.seconds_left(self.status, self.last_confirmed, self.ping_start)

  def request_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    request_type = self.drop_down_1.selected_value
    s, lc, ps, num_emailed = anvil.server.call('add_request', request_type)
    self.status = s
    self.last_confirmed = lc
    self.ping_start = ps
    self.reset_status()
    if self.status == "requesting" and num_emailed > 0:
      self.emailed_notification(num_emailed).show()

  def emailed_notification(self, num):
    """assumes num>0, returns Notification"""
    if num == 1:
      message = ('Someone has been sent a '
                 + 'notification email about your request.')
    else:
      message = (str(num) + ' others have been sent '
                 + 'notification emails about your request.')
    return Notification(message,
                        title='Email notifications sent',
                        timeout=10)

  def renew_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.confirm_wait()

  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.status = None
    self.last_confirmed = None
    self.ping_start = None
    self.tallies = anvil.server.call('cancel')
    self.reset_status()

  def complete_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.status = None
    self.last_confirmed = None
    self.ping_start = None
    self.tallies = anvil.server.call('match_complete')
    self.reset_status()

  def timer_1_tick(self, **event_args):
    """This method is called Every 5.07 seconds"""
    if self.status == "requesting":
      s, lc, ps, self.tallies = anvil.server.call_s('get_status')
      self.status = s
      self.last_confirmed = lc
      self.ping_start = ps
      if self.status != "requesting":
        self.reset_status()
    elif self.status == "pinging":
      self.status = "pinging-pending" # in case server call takes more than a second
      s, lc, ps, self.tallies = anvil.server.call_s('get_status')
      self.status = s
      self.last_confirmed = lc
      self.ping_start = ps
      if self.status != "pinging":
        if self.status == "requesting":
          alert("The other empathy request was cancelled.")
        self.reset_status()
    elif self.status is None:
      self.tallies = anvil.server.call_s('get_tallies')
      self.update_tally_label()

  def timer_2_tick(self, **event_args):
    """This method is called Every 1 seconds"""
    if self.status == "requesting":
      seconds = self.seconds_left()
      self.timer_label.text = ("Your request will expire in:  "
                               + h.seconds_to_digital(seconds) )
      if seconds <= 0:
        self.tallies = anvil.server.call('cancel')
        alert("Request cancelled due to "
              + str(p.WAIT_SECONDS) + " seconds of inactivity.",
              dismissible=False)
        self.status = None
        self.last_confirmed = None
        self.ping_start = None
        self.reset_status()
    elif self.status in ["pinging", "pinging-pending"]:
      seconds = self.seconds_left()
      self.status_label.text = ("Potential match available. Time left for them "
                                + "to confirm:  "
                                + h.seconds_to_digital(seconds))
      if self.status != "pinging-pending" and seconds <= 0:
        self.status = "pinging-pending" # in case server call takes more than a second
        s, lc, ps, self.tallies = anvil.server.call('cancel_other')
        self.status = s
        self.last_confirmed = lc
        self.ping_start = ps
        self.reset_status()

  def confirm_wait(self):
    s, lc, ps, self.tallies = anvil.server.call('confirm_wait')
    self.status = s
    self.last_confirmed = lc
    self.ping_start = ps
    self.reset_status()

  def confirm_match(self, seconds):
    if self.pinged_em_check_box.checked:
      anvil.server.call('pinged_email')
    f = TimerForm(seconds, self.status)
    out = confirm(content=f,
                  title="A match is available. Are you ready?",
                  large=False,
                  dismissible=False)
    if out == True:
      self.status = "matched"
      s, lc, ps, self.tallies = anvil.server.call('match_commenced')
      self.status = s
      self.last_confirmed = lc
      self.ping_start = ps
    elif out in [False, "timer elapsed"]:
      self.tallies = anvil.server.call('cancel')
      self.status = None
      self.last_confirmed = None
      self.ping_start = None
      if out == "timer elapsed":
        alert("A match was found, but the time available for you to confirm ("
              + h.seconds_to_words(p.CONFIRM_MATCH_SECONDS) + ") elapsed.",
              dismissible=False)
    elif out is None:
      self.tallies = anvil.server.call_s('get_tallies')
      self.status = None
      self.last_confirmed = None
      self.ping_start = None
    else:
      print (out)
      assert out == "requesting"
      s, lc, ps, self.tallies = anvil.server.call_s('get_status')
      self.status = s
      self.last_confirmed = lc
      self.ping_start = ps
    self.reset_status()

  def reset_status(self):
    if self.status:
      if self.status != "matched":
        seconds = self.seconds_left()
      self.request_button.visible = False
      self.drop_down_1.enabled = False
      self.drop_down_1.foreground = "gray"
      self.tally_label.visible = False
      self.jitsi_test_check_box.visible = False
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
                                 + h.seconds_to_digital(seconds) )
        self.timer_label.visible = True
        self.complete_button.visible = False
        self.renew_button.visible = True
        self.cancel_button.visible = True
        self.pinged_em_check_box.visible = True
      else:
        if self.status == "pinged":
          return self.confirm_match(seconds)
        assert self.status in ["pinging", "matched"]
        self.note_label.visible = False
        if self.status == "pinging":
          self.status_label.text = ("Potential match available. Time left for them "
                                    + "to confirm:  "
                                    + h.seconds_to_digital(seconds))
          self.set_jitsi_link("")
          self.timer_label.visible = False
          self.status_label.bold = False
          self.renew_button.visible = True
          self.cancel_button.visible = True
          self.complete_button.visible = False
        else:
          assert self.status == "matched"
          self.timer_label.visible = False
          jitsi_code, request_type = anvil.server.call('get_code')
          self.status_label.text = "Status: You have a confirmed match. Use this Jitsi Meet code: "
          self.status_label.bold = True
          self.renew_button.visible = False
          self.cancel_button.visible = False
          self.complete_button.visible = True
          self.set_jitsi_link(jitsi_code)
        self.pinged_em_check_box.visible = False
    else:
      self.status_label.text = "Request an empathy match when ready"
      self.status_label.bold = True
      self.jitsi_test_check_box.visible = True
      self.set_jitsi_link("")
      self.note_label.visible = False
      self.timer_label.visible = False
      self.complete_button.visible = False
      self.renew_button.visible = False
      self.cancel_button.visible = False
      self.request_button.enabled = self.jitsi_test_check_box.checked
      self.request_button.visible = True
      self.drop_down_1.enabled = True
      self.drop_down_1.foreground = "black"
      self.pinged_em_check_box.visible = False
      self.update_tally_label()

  def update_tally_label(self):
    temp = ""
    if self.tallies['receive_first'] > 1:
      if self.tallies['will_offer_first'] > 0:
        temp = (str(self.tallies['receive_first'] + self.tallies['will_offer_first'])
                + ' current requests for an empathy exchange, '
                + 'some of which are requesting a partner willing to offer empathy first.')
      else:
        assert self.tallies['will_offer_first'] == 0
        temp = (str(self.tallies['receive_first'])
                + ' current requests for an empathy exchange, '
                + 'all of which are requesting a partner willing to offer empathy first.')
    elif self.tallies['receive_first'] == 1:
      if self.tallies['will_offer_first'] > 0:
        temp = (str(self.tallies['receive_first'] + self.tallies['will_offer_first'])
                + ' current requests for an empathy exchange. '
                + 'One is requesting a partner willing to offer empathy first.')
      else:
        assert self.tallies['will_offer_first'] == 0
        temp = (str(self.tallies['receive_first'])
                + ' current request for an empathy exchange, '
                + 'requesting a partner willing to offer empathy first.')
    else:
      assert self.tallies['receive_first'] == 0
      if self.tallies['will_offer_first'] > 1:
        temp = (str(self.tallies['will_offer_first'])
                + ' current requests for an empathy exchange, '
                + 'all of which are willing to offer empathy first.')
      elif self.tallies['will_offer_first'] == 1:
        temp = (str(self.tallies['will_offer_first'])
                + ' current request for an empathy exchange '
                + 'by someone willing to offer empathy first.')
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
      else:
        if self.tallies['request_em'] > 1:
          temp += (str(self.tallies['request_em'])
                   + ' people are currently receiving email notifications '
                   + 'about each request for empathy.')
        elif self.tallies['request_em'] == 1:
          temp += (str(self.tallies['request_em'])
                   + ' person is currently receiving email notifications '
                   + 'about each request for empathy.')
    self.tally_label.text = temp
    if len(temp) > 0:
      self.tally_label.visible = True
    else:
      self.tally_label.visible = False

  def set_jitsi_link(self, jitsi_code):
    if jitsi_code == "":
      self.jitsi_link.visible = False
      self.jitsi_link.text = ""
      self.jitsi_link.url = ""
    else:
      self.jitsi_link.url = "https://meet.jit.si/" + jitsi_code
      self.jitsi_link.text = jitsi_code
      self.jitsi_link.visible = True

  def logout_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.logout_user()

  def logout_user(self):
    anvil.users.logout()
    self.status = None
    self.last_confirmed = None
    self.ping_start = None
    self.reset_status()
    open_form('LoginForm')

  def pinged_em_check_box_change(self, **event_args):
    """This method is called when this checkbox is checked or unchecked"""
    anvil.server.call('set_pinged_em', self.pinged_em_check_box.checked)

  def request_em_check_box_change(self, **event_args):
    """This method is called when this checkbox is checked or unchecked"""
    anvil.server.call('set_request_em', self.request_em_check_box.checked)

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

  def jitsi_test_check_box_change(self, **event_args):
    """This method is called when this checkbox is checked or unchecked"""
    self.request_button.enabled = self.jitsi_test_check_box.checked

