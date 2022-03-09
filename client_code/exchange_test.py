import unittest
from . import exchanges
from . import exchange_interactor as ei


# class ExchangeTest(unittest.TestCase):
#   def test_exchange_init(self):
#     an_exchange = exchanges.Exchange("1234", [], [])
#     self.assertEqual(an_exchange.room_code, "1234")
#     self.assertEqual(an_exchange.participants, [])
#     self.assertEqual(an_exchange.requests, [])
    
#   def test_this_participant_initial_slider_value(self):
#     an_exchange = exchanges.Exchange("1234", [], [])
#     self.assertFalse(an_exchange.my_slider_value())


class ExchangeInteractorTest(unittest.TestCase):
  def test_init_match_form(self):
    user_id = "1"

    self.assertEqual(ei.init_match_form(user_id, repo), 
                     (None, None, None, "")
                    )
    