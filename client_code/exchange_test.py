import unittest
from .exchanges import Exchange, Format
from . import exchange_interactor as ei
from .exceptions import RowMissingError
from anvil.tables import app_tables


# class ExchangeTest(unittest.TestCase):
#   def test_exchange_init(self):
#     an_exchange = Exchange("1234", [], [])
#     self.assertEqual(an_exchange.room_code, "1234")
#     self.assertEqual(an_exchange.participants, [])
#     self.assertEqual(an_exchange.requests, [])
    
#   def test_this_participant_initial_slider_value(self):
#     an_exchange = Exchange("1234", [], [])
#     self.assertFalse(an_exchange.my_slider_value())

hugetim_id = app_tables.users.get(email="hugetim@gmail.com").get_id()
poptibo_id = app_tables.users.get(email="poptibo@yahoo.com").get_id()


class MockRepo:
  def __init__(self, db_exchange):
    self._db_exchange = db_exchange
  
  def get_exchange(self, user_id):
    user_ids = [p['user_id'] for p in self._db_exchange.participants]
    if user_id in user_ids:
      return self._db_exchange
    else:
      raise RowMissingError("user_id not found")
  
  def save_exchange(self, exchange):
    self._db_exchange = exchange


class ExchangeInteractorTest(unittest.TestCase):
#   def test_init_match_form_no_status(self):
#     repo = MockRepo(Exchange("eid", None, [dict(user_id="1", present=0, slider_value="")], None, Format(None)))
#     self.assertEqual(ei.init_match_form(poptibo_id, repo), 
#                      (None, None, None, "")
#                     )
    
  def test_init_match_form_matched(self):
    participants = [dict(user_id=poptibo_id, present=0, slider_value=""),
                    dict(user_id=hugetim_id, present=0, slider_value="")]
    e = Exchange("eid", "room code", participants, None, Format(45))
    self.assertEqual(ei.init_match_form(poptibo_id, MockRepo(e)), 
                     (None, "room code", 45, "")
                    )
    self.assertEqual(e.my(poptibo_id)['present'], 1)
    