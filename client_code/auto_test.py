from anvil import *
import anvil.users
import anvil.server
from anvil.tables import app_tables
import unittest
import time
from . import helper as h
from . import portable as port
from . import parameters as p
from datetime import datetime
from . import invites
# from .MenuForm import MenuForm
# from .MenuForm.DashForm import DashForm

class Seconds2WordsTest(unittest.TestCase):
  def test_day(self):
    self.assertEqual(h.seconds_to_words(3600*24), "1 day, 0 seconds")
  
  def test_day_no_seconds(self):
    self.assertEqual(h.seconds_to_words(3600*24, include_seconds=False), "1 day, 0 minutes")
    
  def test_minus(self):
    self.assertEqual(h.seconds_to_words(-1), "minus 1 second")

    
class FullNameTest(unittest.TestCase):
  def test_distance(self):
    for distance in range(1, 5):
      self.assertEqual(
        port.full_name("first", "last", distance),
        "first last" if distance <= 2 else "first"
      )

      
class DatetimeFormatTest(unittest.TestCase):
  def test_remove_zeros(self):
    dt = datetime(2021, 1, 1, 1, 1)
    self.assertEqual(h.time_str(dt), "1:01AM")
    self.assertEqual(h.dow_date_str(dt), "Friday, Jan 1, 2021")
    self.assertEqual(h.day_time_str(dt), "Fri, Jan 1 1:01AM")
    self.assertEqual(h.short_date_str(dt), "1/1/2021")
    
  def test_no_change(self):
    dt = datetime(2020, 12, 31, 10, 10)
    self.assertEqual(h.time_str(dt), "10:10AM")
    self.assertEqual(h.dow_date_str(dt), "Thursday, Dec 31, 2020")
    self.assertEqual(h.day_time_str(dt), "Thu, Dec 31 10:10AM")
    self.assertEqual(h.short_date_str(dt), "12/31/2020")


class RoundUpDatetimeTest(unittest.TestCase):
  def test_round_up(self):
    dt = datetime(2021, 1, 1, 1, 1, 1)
    self.assertEqual(h.round_up_datetime(dt), datetime(2021, 1, 1, 1, 15))
    self.assertEqual(h.round_up_datetime(dt, 30), datetime(2021, 1, 1, 1, 30))
    

class InvitesTest(unittest.TestCase):
  def setUp(self):
    self.user = anvil.users.get_user()
    self.invite1 = invites.Invite(rel_to_inviter='test subject 1', inviter_guess="6666")
    self.invite1.relay('add')
    self.poptibo = app_tables.users.get(email="poptibo@yahoo.com")
    
  def test_url(self):
    invite = invites.Invite(link_key='test')
    self.assertEqual(invite.url, p.URL + "#?invite=test")

  def test_new(self):
    self.assertEqual(self.invite1.inviter.user_id, self.user.get_id())
    self.assertTrue(self.invite1.link_key)

  def test_logged_in_visit(self):
    invite2a = invites.Invite(link_key=self.invite1.link_key)
    errors = invite2a.relay('visit', {'user': self.poptibo})
    self.assertTrue(errors)
    self.assertEqual(errors[0], "The inviter did not accurately provide the last 4 digits of your phone number.")

    self.invite1.inviter_guess = self.poptibo['phone'][-4:]
    self.invite1.relay()
    invite2b = invites.Invite(link_key=invite1.link_key)
    errors = invite2b.relay('visit', {'user': self.poptibo})
    self.assertEqual(invite2a.invitee.user_id, self.poptibo.get_id())
    self.assertFalse(errors)
#     errors = invite2b.relay('sc_cancel_response')
#     invite2b.assertFalse(invite2b.invitee)
#     self.assertFalse(errors)

#   def test_new_visit(self):
#     invite2c = invites.Invite(link_key=invite1.link_key)
#     errors = self.invite2c.relay('visit', {'user': None})
#     self.assertFalse(errors)
#     self.invite2c.assertFalse(invite2c.invitee)
#     self.invite2c.cancel_response()
#     errors = self.invite2c.relay()
#     self.assertFalse(errors)
    
#   def test_connect_invite(self):
#     port_user = anvil.server.call('get_port_user', self.user, 0)
#     port_invitee = anvil.server.call('get_port_user', self.poptibo, user1_id=self.user.get_id())
#     invite3 = invites.Invite(inviter=port_user, rel_to_inviter='test subject 3', inviter_guess="5555", invitee=port_invitee)
#     errors = invite3.relay()
#     self.assertFalse(errors)
    
#   def test_connect_response(self):
#     self.test_connect_invite()
#     invite3 = invites.Invite.from_inviter(inviter_id=self.user.get_id(), user_id=self.poptibo.get_id())
#     self.assertTrue(invite3)
#     invite3['invitee_guess'] = "6688"
#     invite3['rel_to_invitee'] = "tester 3"
#     errors = invite3.relay()
#     self.assertFalse(errors)
#     connection_records = anvil.server.call('get_connections')
#     self.assertTrue([r for r in connection_records if r.user_id == self.poptibo.get_id()])
#     anvil.server.call('disconnect', self.poptibo.get_id())

  def tearDown(self):
    self.invite1.relay('cancel')
    self.assertFalse(self.invite1.inviter)


def client_auto_tests():
  pass
#   Seconds2WordsTest().main()
#   FullNameTest().main()
  
  
def test_alert(content, handler):
  content.set_event_handler('x-close-alert', handler)
  
  
class TestNow():

  def setUp(self):
    self.top_form = get_open_form()
    self.top_form.home_link_click()

  def test_repeat_now_proposal(self):
    for email, user_id in self.top_form.test_requestuser_drop_down.items:
      if email == "hugetim@alumni.rice.edu":
        accept_user_id = user_id
    for i in range(2):
      anvil.server.call('add_now_proposal')
      time.sleep(15)
      anvil.server.call('accept_now_proposal', user_id=accept_user_id)
      time.sleep(10)
      anvil.server.call('cancel', user_id=accept_user_id)
      time.sleep(10)
      anvil.server.call('cancel')
      time.sleep(15)
      
      
  def test_multiple_proposal_times(self):
    self.top_form.content.propose_button_click()
    time.sleep(5)
    self.top_form.proposal_alert.button_add_alternate_click()
    time.sleep(5)
    self.top_form.proposal_alert.save_button_click()

def run_now_test():
  #unittest.main()
  #print("run manually")
  test = TestNow()
  test.setUp()
  test.test_repeat_now_proposal()
  #test.test_multiple_proposal_times()

# class TestNow(unittest.TestCase):

#   def setUp(self):
#     self.top_form = get_open_form()
#     self.top_form.go_dash()

#   def test_add_my_now_proposal(self):
#     self.top_form.content.propose_button_click()
#     focused_component = get_focused_component()
#     print(focused_component.__dict__())
#     #self.assertEqual( multiply(3,4), 12)


# def run_tests():
#   unittest.main()