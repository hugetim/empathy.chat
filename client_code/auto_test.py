from anvil import *
import anvil.server
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
    

class InviteTest(unittest.TestCase):
  def test_url(self):
    invite = invites.Invite(link_key='test')
    self.assertEqual(invite.url, p.URL + "#?invite=test")

  def test_update(self):
    invite1 = invites.Invite(invite_id="1")
    invite2 = invites.Invite()
    invite2.update(invite1)
    self.assertEqual(invite2.invite_id, "1")
    
  def test_invalid_invite(self):
    invite1 = invites.Invite()
    invite2 = invites.Invite(rel_to_inviter="12", inviter_guess="1234")
    invite3 = invites.Invite(rel_to_inviter="12345678", inviter_guess="1")
    invite4 = invites.Invite(rel_to_inviter="12345678", inviter_guess="1234")
    invite5 = invites.Invite(rel_to_invitee="12345678", invitee_guess="1234")
    self.assertEqual(len(invite1.invalid_invite()), 2)
    self.assertEqual(invite2.invalid_invite(), ["Please add a description of your relationship."])
    self.assertEqual(invite3.invalid_invite(), ["Wrong number of digits entered."])
    self.assertFalse(invite4.invalid_invite())
    self.assertTrue(invite4.invalid_response())
    self.assertFalse(invite5.invalid_response())

  def test_rel_item(self):
    invite1 = invites.Invite(rel_to_inviter="12345678", inviter_guess="1234")
    item1 = invite1.rel_item(for_response=False)
    self.assertEqual(item1['relationship'], invite1.rel_to_inviter)
    self.assertEqual(item1['phone_last4'], invite1.inviter_guess)
#     self.assertEqual(item1['name'], invite1.invitee.name if invite1.invitee else "")
    item2 = invite1.rel_item(for_response=True)
    self.assertEqual(item2['relationship'], invite1.rel_to_invitee)
    self.assertEqual(item2['phone_last4'], invite1.invitee_guess)
#     self.assertEqual(item2['name'], invite1.inviter.name if invite1.inviter else "")
    
    item1['relationship'] = "abcdefgh"
    item1['phone_last4'] = "4321"
    item2['relationship'] = "1234efgh"
    invite1.update_from_rel_item(item1, for_response=False)
    invite1.update_from_rel_item(item2, for_response=True)
    self.assertEqual(invite1.rel_to_inviter, item1['relationship'])
    self.assertEqual(invite1.inviter_guess, item1['phone_last4'])
    self.assertEqual(invite1.rel_to_invitee, item2['relationship'])

    
# class MyGroupsTest(unittest.TestCase):
#   def setUp(self):
#     pass
#     #self.my_groups = groups.MyGroups()
#     #self.my_groups.relay('load')
    
#   def test_get_items(self):
#     items = self.my_groups.drop_down_items()
    
#   def test_add_group(self):
#     new_group = self.my_groups.add_group()
#     self.assertEqual(new_group['name'], "New Group")


def client_auto_tests():
  from anvil_extras.utils import timed
  
  @timed
  def tests_run_client_side():
    from . import exchange_controller_test as ect
    ect.ExchangeControllerTest().main()
  #   Seconds2WordsTest().main()
  #   FullNameTest().main()
  tests_run_client_side()
  
  
def test_alert(content, handler):
  content.set_event_handler('x-close-alert', handler)
  
  
class TestNow(): #not unittest.TestCase
  def setUp(self):
    self.top_form = get_open_form()
    self.top_form.home_link_click()

  def test_repeat_now_proposal(self):
    accept_user_id = self.top_form.test_requestuser_drop_down.items[0][1]
    for i in range(2):
      anvil.server.call('add_now_proposal')
      time.sleep(15)
      anvil.server.call('accept_now_proposal', user_id=accept_user_id)
      time.sleep(15)
      anvil.server.call('cancel_accept', user_id=accept_user_id)
      time.sleep(10)
      anvil.server.call('cancel_now')
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


#def run_tests():
#   unittest.main()