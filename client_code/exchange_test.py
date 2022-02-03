import unittest
from . import exchanges

class ExchangeTest(unittest.TestCase):
  def test_exchange_init(self):
    an_exchange = exchanges.Exchange("1234", [], [])
    self.assertEqual(an_exchange.room_code, "1234")
    self.assertEqual(an_exchange.participants, [])
    self.assertEqual(an_exchange.requests, [])
    
  def test_this_participant(self):
    an_exchange = exchanges.Exchange("1234", [], [])
    self.assertFalse(an_exchange.my_slider_value())
    