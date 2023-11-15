from anvil import *
import anvil.server
import time


class TestNow(): #not unittest.TestCase
  def setUp(self):
    self.top_form = get_open_form()
    self.top_form.home_link_click()

  def test_repeat_now_proposal(self):
    accept_user_id = anvil.server.call('get_test_user_id')
    for i in range(2):
      anvil.server.call('add_now_proposal_old')
      time.sleep(15)
      anvil.server.call('accept_now_proposal_old', user_id=accept_user_id)
      time.sleep(15)
      anvil.server.call('ping_cancel', user_id=accept_user_id)
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
  test = TestNow()
  test.setUp()
  test.test_repeat_now_proposal()
  #test.test_multiple_proposal_times()
