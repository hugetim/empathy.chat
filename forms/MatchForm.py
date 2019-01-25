from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.server
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.users
import datetime
from TimerForm import TimerForm
import parameters as p
import anvil.tz

class MatchForm(MatchFormTemplate):
  user_id = None
  trust_level = 0
  tallies =    dict(receive_first = 0,
                 will_offer_first = 0,
                 request_em = 0)
  status = None
  last_confirmed = None # this or other_last_confirmed, whichever is earlier
  ping_start = None


  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)

    self.user_id = anvil.users.get_user().get_id()
    # 'prune' initializes new users to trust level 0 (via 'get_trust_level')
    self.confirming_wait = False
    tl, re, me, tallies, rt, s, lc, ps, e = anvil.server.call('prune',self.user_id)
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
### old "pinging" code: prune should ensure this is not the case, changing status accordingly
# if self.seconds_left<=0:
#   self.current_status, ref_time, self.tallies, alt_avail = anvil.server.call('cancel_other',self.user_id)

### old "pinged" code: should never be after prune-change to matched, requesting, or none
       #   timer = datetime.datetime.now(ref_time.tzinfo) - ref_tim
          # if alt_avail and timer.seconds > p.CONFIRM_MATCH_SECONDS:
          #   self.seconds_left = 2*p.CONFIRM_WAIT_SECONDS
          #   self.current_status = anvil.server.call('cancel_match',self.user_id)
          # else:
          #   self.seconds_left = 2*p.CONFIRM_WAIT_SECONDS
          #   if alt_avail:
          #     seconds_left = p.CONFIRM_MATCH_SECONDS - timer.seconds
          #   else:
          #     seconds_left = self.seconds_left
          #   self.confirm_match(seconds_left)

  def seconds_left():
    'derive seconds_left from status, last_confirmed, and ping_start'
    now = datetime.datetime.now(ref_time.tzinfo)
    if self.status in ["pinging-mult", "pinging-one", "pinged-mult", "pinged-one"]:
      min_confirm_match = p.CONFIRM_MATCH_SECONDS - (now - self.ping_start).seconds
      if self.status=="pinging-mult":
        return min_confirm_match + p.BUFFER_SECONDS
      elif self.status=="pinged-mult":
        return min_confirm_match
    wait_time = p.CONFIRM_WAIT_SECONDS - (now - self.last_confirmed).seconds
    if self.status=="pinging-one":
      return max(min_confirm_match, joint_wait_time) + p.BUFFER_SECONDS
    elif self.status=="pinged-one":
      return max(min_confirm_match, joint_wait_time)
    elif self.status in ["requesting", "requesting-confirm"]:
      return wait_time
    else:
      print("MatchForm.seconds_left(): " + self.status)

  def request_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    request_type = self.drop_down_1.selected_value
    jitsi_code, s, lc, ps, num_emailed = anvil.server.call('add_request',
                                                           self.user_id,
                                                           request_type)
    self.status = s
    self.last_confirmed = lc
    self.ping_start = ps
    if s == None and num_emailed > 0:
      self.emailed_notification(num_emailed).show()
    self.reset_status()
    ## This logic should be handled server-side
    #  timer = datetime.datetime.now(last_confirmed.tzinfo) - last_confirmed
    #  if timer.seconds <= p.BUFFER_SECONDS:
    #    self.current_status = "empathy"

  def emailed_notification(self, num):
    'assumes num>0, returns Notification'
    if num_emailed==1:
      message = ('Someone has been sent a '
                 + 'notification email about your request.')
    else:
      message = (str(num_emailed) + ' others have been sent '
                 + 'notification emails about your request.')
    return Notification(message,
                        title='Email notifications sent',
                        timeout=10)

  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.status = None
    self.tallies = anvil.server.call('cancel',self.user_id)
    self.reset_status()

  def complete_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.status = None
    self.tallies = anvil.server.call('match_complete',self.user_id)
    self.reset_status()

  def timer_1_tick(self, **event_args):
    """This method is called Every 5 seconds"""
    if self.current_status in ["requesting", "offering"] and self.confirming_wait==False:
      new_status, ref_time, n, alt_avail = anvil.server.call_s('get_status',self.user_id)
      if new_status == "pinged":
        if self.match_em_check_box.checked:
          anvil.server.call('match_email')
        self.current_status = new_status
        if alt_avail:
          seconds_left = p.CONFIRM_MATCH_SECONDS
        else:
          timer = datetime.datetime.now(ref_time.tzinfo) - ref_time
          seconds_left = 2*p.CONFIRM_WAIT_SECONDS - timer.seconds
        self.confirm_match(seconds_left)
      elif new_status in ["empathy", None]:
        self.current_status = new_status
        self.tallies = n
      elif new_status != self.current_status:
        print new_status
      if self.current_status not in ["requesting", "offering"]:
        self.set_form_status(self.current_status)
    elif self.current_status == "matched":
      new_status, ref_time, n, alt_avail = anvil.server.call_s('get_status',self.user_id)
      if new_status in ["requesting", "offering"]:
        if new_status=="requesting":
          alert("The empathy offer was cancelled.")
        else:
          alert("The empathy request was cancelled.")
        self.current_status = new_status
        timer = datetime.datetime.now(ref_time.tzinfo) - ref_time
        self.seconds_left = 2*p.CONFIRM_WAIT_SECONDS - timer.seconds
        self.set_form_status(self.current_status)
      elif new_status in ["empathy", None]:
        self.current_status = new_status
        self.tallies = n
        self.set_form_status(self.current_status)
      elif new_status != self.current_status:
        print new_status
      else:
        timer = datetime.datetime.now(ref_time.tzinfo) - ref_time
        if alt_avail:
          self.seconds_left = p.CONFIRM_MATCH_SECONDS + p.BUFFER_SECONDS - timer.seconds
        else:
          self.seconds_left = 2*p.CONFIRM_WAIT_SECONDS + p.BUFFER_SECONDS - timer.seconds
    elif self.current_status == None:
      self.update_tally_label()

  def timer_2_tick(self, **event_args):
    """This method is called Every 1 seconds"""
    if self.current_status in ["requesting", "offering"]:
      self.seconds_left -= 1
      if self.seconds_left<=p.CONFIRM_WAIT_SECONDS and self.confirming_wait==False:
        self.confirm_wait()
    elif self.current_status == "matched":
      self.seconds_left -= 1
      self.timer_label.text = ("A match has been found and they have up to "
                               + str(self.seconds_left) + " seconds to confirm.")
      if self.seconds_left<=0:
        self.current_status, ref_time, self.tallies, alt_avail = anvil.server.call('cancel_other',self.user_id)
        now = datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc())
        timer = now - self.last_confirmed
        self.seconds_left = 2*p.CONFIRM_WAIT_SECONDS - timer.seconds
        self.set_form_status(self.current_status)

  def confirm_wait(self):
    assert self.current_status in ["requesting", "offering"]
    self.confirming_wait = True
    now = datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc())
    timer = now - self.last_confirmed
    self.seconds_left = 2*p.CONFIRM_WAIT_SECONDS - timer.seconds
    f = TimerForm(self.seconds_left, self.user_id, self.current_status)
    out = confirm(content=f,
                  title="Continue waiting for a match?",
                  large=False,
                  dismissible=False)
    if out==True:
      anvil.server.call('confirm_wait',self.user_id)
      self.seconds_left = 2*p.CONFIRM_WAIT_SECONDS
      self.last_confirmed = datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc())
      self.set_form_status(self.current_status)
    elif out==False:
      anvil.server.call('cancel',self.user_id)
      self.current_status = None
      self.set_form_status(self.current_status)
    elif out=="timer elapsed" or out==None:
      anvil.server.call('cancel',self.user_id)
      self.current_status = None
      alert("Request cancelled due to "
            + str(2*p.CONFIRM_WAIT_SECONDS) + " seconds of inactivity.",
            dismissible=False)
      self.set_form_status(self.current_status)
    else:
      print out
      assert out in ["pinged","alt pinged","empathy"]
      self.current_status = out
      alt_avail = False
      if out=="alt pinged":
        self.current_status = "pinged"
        alt_avail = True
      if out in ["pinged","alt pinged"]:
        if self.match_em_check_box.checked:
          anvil.server.call('match_email')
        if alt_avail:
          seconds_left = p.CONFIRM_MATCH_SECONDS
        else:
          seconds_left = self.seconds_left
        self.confirm_match(seconds_left)
      if self.current_status not in ["requesting", "offering"]:
        self.set_form_status(self.current_status)
    self.confirming_wait = False

  def confirm_match(self, seconds):
    assert self.current_status=="pinged"
    f = TimerForm(seconds, self.user_id, self.current_status)
    out = confirm(content=f,
                  title="A match is available. Are you ready?",
                  large=False,
                  dismissible=False)
    if out==True:
      self.current_status = "empathy"
    elif out==False or out=="timer elapsed":
      anvil.server.call('cancel',self.user_id)
      self.current_status = None
    elif out=="alt timer elapsed":
      self.current_status = anvil.server.call('cancel_match',self.user_id)
      alert("A match was found, but the time available for you to confirm ("
            + str(p.CONFIRM_MATCH_SECONDS) + " seconds) elapsed.",
            dismissible=False)
    else:
      print out
      assert out in [None, "requesting", "offering"]
      self.current_status = out
    if out in ["alt timer elapsed", "requesting", "offering"]:
      now = datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc())
      timer = now - self.last_confirmed
      self.seconds_left = 2*p.CONFIRM_WAIT_SECONDS - timer.seconds

  def reset_status(self):
    if self.status:
      if self.status != "matched":
        self.seconds_left = self.seconds_left()
      self.request_button.visible = False
      self.drop_down_1.enabled = False
      self.drop_down_1.foreground = "gray"
      self.tally_label.visible = False
      if self.status in ["requesting", "requesting-confirm"]:
        self.status.text = ("Status: Requesting an empathy exchange. ")
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
      else:
        assert self.status in ["pinging-one", "pinging-mult", "matched"]
        self.note_label.visible = False
        if self.status in ["pinging-one", "pinging-mult"]:
          self.timer_label.text = ("A match has been found and they have up to "
                                   + str(self.seconds_left) + " seconds to confirm.")
          self.timer_label.visible = True
          self.status.text = "A match should be ready soon. Set up Jitsi at: "
          self.status.bold = False
          jitsi_code, request_type = anvil.server.call('get_code', self.user_id)
          self.cancel_button.visible = True
          self.complete_button.visible = False
        else:
          assert self.status=="matched"
          self.timer_label.visible = False
          (new_status, match_start,
           jitsi_code, request_type) = anvil.server.call('match_commenced',
                                                         self.user_id)
          if new_status != "empathy":
            assert new_status != "matched"
            self.current_status = new_status
            return self.set_form_status(self.current_status)
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
    self.tallies = anvil.server.call_s('get_tallies')
    temp = ""
    if self.tallies['requesting'] > 1:
      if self.tallies['offering'] > 0:
        temp = (str(self.tallies['requesting'] + self.tallies['offering'])
                + ' current requests for an empathy exchange, '
                + 'some of which are requesting a partner willing to offer empathy first.')
      else:
        assert self.tallies['offering']==0
        temp = (str(self.tallies['requesting'])
                + ' current requests for an empathy exchange, '
                + 'all of which are requesting a partner willing to offer empathy first.')
    elif self.tallies['requesting']==1:
      if self.tallies['offering'] > 0:
        temp = (str(self.tallies['requesting'] + self.tallies['offering'])
                + ' current requests for an empathy exchange. '
                + 'One is requesting a partner willing to offer empathy first.')
      else:
        assert self.tallies['offering']==0
        temp = (str(self.tallies['requesting'])
                + ' current request for an empathy exchange, '
                + 'requesting a partner willing to offer empathy first.')
    else:
      assert self.tallies['requesting']==0
      if self.tallies['offering'] > 1:
        temp = (str(self.tallies['offering'])
                + ' current requests for an empathy exchange, '
                + 'all of which are willing to offer empathy first.')
      elif self.tallies['offering']==1:
        temp = (str(self.tallies['offering'])
                + ' current request for an empathy exchange '
                + 'by someone willing to offer empathy first.')
      else:
        assert self.tallies['offering']==0
    if self.tallies['offering']==0:
      if self.tallies['requesting'] > 0:
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
