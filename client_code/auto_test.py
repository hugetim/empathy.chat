from anvil import *
import anvil.server
import unittest
import time

    
# class MyGroupsTest(unittest.TestCase):
#   def setUp(self):
#     pass
#     #self.my_groups = groups.MyGroups()
#     #self.my_groups = anvil.server.call('load_my_groups)
    
#   def test_get_items(self):
#     items = self.my_groups.drop_down_items()
    
#   def test_add_group(self):
#     new_group = self.my_groups.add_group()
#     self.assertEqual(new_group['name'], "New Group")


# def client_auto_tests():
#   from anvil_extras.utils import timed
  
#   @timed
#   def tests_run_client_side():
#     from . import exchange_controller_test as ect
#     ect.ExchangeControllerTest().main()
#   tests_run_client_side()
  
  
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