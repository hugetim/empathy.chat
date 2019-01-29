from anvil import *
import anvil.google.auth, anvil.google.drive
import anvil.server
import anvil.users
from TimerForm import TimerForm
import parameters as p
import anvil.tz
import helper as h


class MatchForm(MatchFormTemplate):
  user_id = None
  trust_level = 0
  tallies = dict(receive_first = 0,
                 will_offer_first = 0,
                 request_em = 0)
  status = None
  last_confirmed = None # this or other_last_confirmed, whichever is earlier
  ping_start = None
  seconds = None

  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)

    self.user_id = anvil.users.get_user().get_id()
    # 'prune' initializes new users to trust level 0 (via 'get_trust_level')
    self.confirming_wait = False
    tl, re, me, rt, s, lc, ps, tallies, e = anvil.server.call('prune',self.user_id)
    if e==False:
      alert('Your email address is not approved to use this app. '
            + 'Contact empathyroom@gmail.com for help.')
      self.logout_user()
    self.trust_level = tl
    if self.trust_level >= p.TEST_TRUST_LEVEL:
      self.test_mode.visible = True
    self.request_em_check_box.checked = re
    self.match_em_check_box.checked = me
    self.tallies = tallies
    self.self.drop_down_1.selected_value = rt
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
    s, lc, ps, num_emailed = anvil.server.call('add_request',
                                               self.user_id,
                                               request_type)
    self.status = s
    self.last_confirmed = lc
    self.ping_start = ps
    if self.status=="requesting" and num_emailed > 0:
      self.emailed_notification(num_emailed).show()
    self.reset_status()

  def emailed_notification(self, num):
    """assumes num>0, returns Notification"""
    if num==1:
      message = ('Someone has been sent a '
                 + 'notification email about your request.')
    else:
      message = (str(num) + ' others have been sent '
                 + 'notification emails about your request.')
    return Notification(message,
                        title='Email notifications sent',
                        timeout=10)

  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.status = None
    self.last_confirmed = None
    self.ping_start = None
    self.tallies = anvil.server.call('cancel',self.user_id)
    self.reset_status()

  def complete_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.status = None
    self.last_confirmed = None
    self.ping_start = None
    self.tallies = anvil.server.call('match_complete',self.user_id)
    self.reset_status()

  def timer_1_tick(self, **event_args):
    """This method is called Every 5 seconds"""
    if self.status=="requesting":
      s, lc, ps, self.tallies = anvil.server.call_s('get_status',self.user_id)
      self.status = s
      self.last_confirmed = lc
      self.ping_start = ps
      if self.status=="requesting":
        self.seconds = self.seconds_left()
      else:
        self.reset_status()
    elif self.status in ["pinging-one", "pinging-mult"]:
      self.status = "pinging-pending" # in case server call takes more than a second
      s, lc, ps, self.tallies = anvil.server.call_s('get_status',self.user_id)
      self.status = s
      self.last_confirmed = lc
      self.ping_start = ps
      if self.status in ["pinging-one", "pinging-mult"]:
        self.seconds = self.seconds_left()
      else:
        if self.status=="requesting":
          alert("The other empathy request was cancelled.")
        self.reset_status()
    elif self.status is None:
      self.tallies = anvil.server.call_s('get_tallies')
      self.update_tally_label()

  def timer_2_tick(self, **event_args):
    """This method is called Every 1 seconds"""
    if self.status=="requesting":
      self.seconds -= 1
      if self.seconds <= p.CONFIRM_WAIT_SECONDS:
        self.status = "requesting-confirm"
        self.reset_status()
    elif self.status in ["pinging-one", "pinging-mult"]:
      self.seconds -= 1
      self.timer_label.text = ("A match has been found and they have up to "
                               + str(self.seconds) + " seconds to confirm.")
      if self.seconds<=0:
        self.status = "pinging-pending" # in case server call takes more than a second
        s, lc, ps, self.tallies = anvil.server.call('cancel_other',self.user_id)
        self.status = s
        self.last_confirmed = lc
        self.ping_start = ps
        self.reset_status()

  def confirm_wait(self):
    f = TimerForm(self.seconds, self.user_id, self.status)
    out = confirm(content=f,
                  title="Continue waiting for a match?",
                  large=False,
                  dismissible=False)
    if out==True:
      self.last_confirmed = anvil.server.call('confirm_wait',self.user_id)
      self.status = "requesting"
    elif out in [False, "timer elapsed", None]:

      self.tallies = anvil.server.call('cancel',self.user_id)
      if out in ["timer elapsed", None]:
        alert("Request cancelled due to "
              + str(p.WAIT_SECONDS) + " seconds of inactivity.",
              dismissible=False)
      self.status = None
      self.last_confirmed = None
      self.ping_start = None
    else:
      print (out)
      assert out in ["pinged-one","pinged-mult","matched"]
      if out in ["pinged-one","pinged-mult"]:
        s, lc, ps, self.tallies = anvil.server.call_s('get_status',self.user_id)
        self.status = s
        self.last_confirmed = lc
        self.ping_start = ps
      else:
        self.status = out
        assert self.status == "matched"
        anvil.server.call('match_commenced', self.user_id)
  self.reset_status()

  def confirm_match(self):
    if self.match_em_check_box.checked:
      anvil.server.call('match_email')
    f = TimerForm(self.seconds, self.user_id, self.status)
    out = confirm(content=f,
                  title="A match is available. Are you ready?",
                  large=False,
                  dismissible=False)
    if out==True:
      self.status = "matched"
      anvil.server.call('match_commenced', self.user_id)
    elif out in [False, "timer elapsed"]:
      self.tallies = anvil.server.call('cancel',self.user_id)
      self.status = None
      self.last_confirmed = None
      self.ping_start = None
    elif out=="alt timer elapsed":
      s, lc, ps, self.tallies = anvil.server.call('cancel_match',self.user_id)
      alert("A match was found, but the time available for you to confirm ("
            + str(p.CONFIRM_MATCH_SECONDS) + " seconds) elapsed.",
            dismissible=False)
      self.status = s
      self.last_confirmed = lc
      self.ping_start = ps
    elif out is None:
      self.tallies = anvil.server.call_s('get_tallies')
      self.status = None
      self.last_confirmed = None
      self.ping_start = None
    else:
      print (out)
      assert out in ["requesting", "requesting-confirm"]
      s, lc, ps, self.tallies = anvil.server.call_s('get_status',self.user_id)
      self.status = s
      self.last_confirmed = lc
      self.ping_start = ps
    self.reset_status()

  def reset_status(self):
    if self.status:
      if self.status != "matched":
        self.seconds = self.seconds_left()
      self.request_button.visible = False
      self.drop_down_1.enabled = False
      self.drop_down_1.foreground = "gray"
      self.tally_label.visible = False
      if self.status in ["requesting", "requesting-confirm"]:
        self.status.text = "Status: Requesting an empathy exchange. "
        self.note_label.text = ("(Note: Your request will be cancelled after "
                                + str(2*p.CONFIRM_WAIT_SECONDS/60)
                                + " minutes of inactivity. After "
                                + str(p.CONFIRM_WAIT_SECONDS/60)
                                + " minutes, a dialog will appear allowing "
                                + "you to refresh your request. "
                                + "Also, you will only have "
                                + str(p.CONFIRM_MATCH_SECONDS)
                                + " seconds to confirm a match if someone "
                                + "else is available to take your place.)")
        self.note_label.visible = True
        self.status.bold = False
        self.set_jitsi_link("")
        self.timer_label.visible = False
        self.complete_button.visible = False
        self.cancel_button.visible = True
        self.match_em_check_box.visible = True
        if self.status=="requesting-confirm":
          return self.confirm_wait()
      else:
        if self.status in ["pinged-one", "pinged-mult"]:
          return self.confirm_match()
        assert self.status in ["pinging-one", "pinging-mult", "matched"]
        self.note_label.visible = False
        if self.status in ["pinging-one", "pinging-mult"]:
          self.timer_label.text = ("A match has been found and they have up to "
                                   + str(self.seconds) + " seconds to confirm.")
          self.timer_label.visible = True
          self.status.text = "A match should be ready soon. Set up Jitsi at: "
          self.status.bold = False
          jitsi_code, request_type = anvil.server.call('get_code', self.user_id)
          self.cancel_button.visible = True
          self.complete_button.visible = False
        else:
          assert self.status=="matched"
          self.timer_label.visible = False
          jitsi_code, request_type = anvil.server.call('get_code', self.user_id)
          self.status.text = "You have a confirmed match. Use Jitsi to meet: "
          self.status.bold = True
          self.cancel_button.visible = False
          self.complete_button.visible = True
        self.set_jitsi_link(jitsi_code)
        self.match_em_check_box.visible = False
    else:
      self.status.text = "Request a match when ready:"
      self.status.bold = True
      self.note_label.visible = False
      self.set_jitsi_link("")
      self.timer_label.visible = False
      self.complete_button.visible = False
      self.cancel_button.visible = False
      self.request_button.visible = True
      self.drop_down_1.enabled = True
      self.drop_down_1.foreground = "black"
      self.match_em_check_box.visible = False
      self.update_tally_label()

  def update_tally_label(self):
    temp = ""
    if self.tallies['receive_first'] > 1:
      if self.tallies['will_offer_first'] > 0:
        temp = (str(self.tallies['receive_first'] + self.tallies['will_offer_first'])
                + ' current requests for an empathy exchange, '
                + 'some of which are requesting a partner willing to offer empathy first.')
      else:
        assert self.tallies['will_offer_first']==0
        temp = (str(self.tallies['receive_first'])
                + ' current requests for an empathy exchange, '
                + 'all of which are requesting a partner willing to offer empathy first.')
    elif self.tallies['receive_first']==1:
      if self.tallies['will_offer_first'] > 0:
        temp = (str(self.tallies['receive_first'] + self.tallies['will_offer_first'])
                + ' current requests for an empathy exchange. '
                + 'One is requesting a partner willing to offer empathy first.')
      else:
        assert self.tallies['will_offer_first']==0
        temp = (str(self.tallies['receive_first'])
                + ' current request for an empathy exchange, '
                + 'requesting a partner willing to offer empathy first.')
    else:
      assert self.tallies['receive_first']==0
      if self.tallies['will_offer_first'] > 1:
        temp = (str(self.tallies['will_offer_first'])
                + ' current requests for an empathy exchange, '
                + 'all of which are willing to offer empathy first.')
      elif self.tallies['will_offer_first']==1:
        temp = (str(self.tallies['will_offer_first'])
                + ' current request for an empathy exchange '
                + 'by someone willing to offer empathy first.')
      else:
        assert self.tallies['will_offer_first']==0
    if self.tallies['will_offer_first']==0:
      if self.tallies['receive_first'] > 0:
        if self.tallies['request_em'] > 1:
          temp += (str(self.tallies['request_em'])
                   + ' others are currently receiving email notifications '
                   + 'about each request for empathy.')
        elif self.tallies['request_em']==1:
          temp += (str(self.tallies['request_em'])
                   + ' other person is currently receiving email notifications '
                   + 'about each request for empathy.')
      else:
        if self.tallies['request_em'] > 1:
          temp += (str(self.tallies['request_em'])
                   + ' people are currently receiving email notifications '
                   + 'about each request for empathy.')
        elif self.tallies['request_em']==1:
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
      self.jitsi_link.text = self.jitsi_link.url
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
    self.user_id = None
    open_form('LoginForm')

  def match_em_check_box_change(self, **event_args):
    """This method is called when this checkbox is checked or unchecked"""
    anvil.server.call('set_match_em', self.match_em_check_box.checked)

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
    user = self.test_requestuser_drop_down.selected_value
    requesttype = self.test_requesttype_drop_down.selected_value
    if user and requesttype:
      anvil.server.call('test_add_request', user, requesttype)
    else:
      alert("User and request type required to add request.")

  def test_clear_click(self, **event_args):
    """This method is called when the button is clicked"""
    anvil.server.call('test_clear')
    self.test_requestuser_drop_down_refresh()

  def test_requestuser_drop_down_refresh(self):
    out = anvil.server.call('test_get_user_list')
    self.test_requestuser_drop_down.items = out
