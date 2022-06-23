import unittest
from .exchanges import Exchange, Format
from . import exchange_interactor as ei
from .exchange_gateway import ExchangeRepository
from .exceptions import RowMissingError
from anvil.tables import app_tables
from .server_misc import now
from anvil import secrets


# class ExchangeTest(unittest.TestCase):
#   def test_exchange_init(self):
#     an_exchange = Exchange("1234", [], [])
#     self.assertEqual(an_exchange.room_code, "1234")
#     self.assertEqual(an_exchange.participants, [])
#     self.assertEqual(an_exchange.requests, [])
    
#   def test_this_participant_initial_slider_value(self):
#     an_exchange = Exchange("1234", [], [])
#     self.assertFalse(an_exchange.my_slider_value())

hugetim_id = app_tables.users.get(email=secrets.get_secret('admin_email')).get_id()
poptibo_id = app_tables.users.get(email=secrets.get_secret('test_user2_email')).get_id()


class MockRepo:
  def __init__(self, db_exchange):
    self._db_exchange = db_exchange
  
  def get_exchange(self, user_id):
    user_ids = [p['user_id'] for p in self._db_exchange.participants]
    if user_id in user_ids:
      return Exchange(self._db_exchange.exchange_id, self._db_exchange.room_code, self._db_exchange.participants, 
                      self._db_exchange.start_now, self._db_exchange.start_dt, self._db_exchange.exchange_format,
                      user_id)
    else:
      raise RowMissingError("user_id not found")
  
  def save_exchange(self, exchange):
    self._db_exchange = Exchange(exchange.exchange_id, exchange.room_code, exchange.participants,
                                 exchange.start_now, exchange.start_dt, exchange.exchange_format,
                                 exchange.my['user_id'], exchange._my_i)
    
  def get_chat_messages(self, exchange):
    return []


class TestInitMatch(unittest.TestCase):
  def test_init_match_form_no_status(self):
    participants = [dict(user_id="1", present=0, slider_value=""),
                    dict(user_id="2", present=0, slider_value="")]
    ei.repo = MockRepo(Exchange("eid", None, participants, False, None, Format(None), "1"))
    self.assertEqual(ei.init_match_form(poptibo_id), 
                     (None, None, None, "")
                    )
    
  def test_init_match_form_matched(self):
    participants = [dict(user_id=poptibo_id, present=0, slider_value=""),
                    dict(user_id=hugetim_id, present=0, slider_value="")]
    e = Exchange("eid", "room code", participants, False, None, Format(45), poptibo_id)
    ei.repo = MockRepo(e)
    self.assertEqual(ei.init_match_form(poptibo_id), 
                     (None, "room code", 45, "")
                    )
    self.assertEqual(e.my['present'], 1)

  def tearDown(self):
    restore_repo()

    
class TestUpdateMatch(unittest.TestCase):
  def test_update_match_form_matched(self):
    participants = [dict(user_id=poptibo_id, present=0, slider_value=.2),
                    dict(user_id=hugetim_id, present=1, slider_value="", external=1, complete=0, late_notified=1)]
    e = Exchange("eid", "room code", participants, False, now(), Format(45), poptibo_id)
    ei.repo = MockRepo(e)
    self.assertEqual(ei.update_match_form(poptibo_id), 
                     dict(status="matched",
                          how_empathy_list=["test how", "test how_empathy"],
                          their_name="Tim",
                          message_items=[],
                          my_slider_value=.2,
                          their_slider_value="",
                          their_external=1,
                          their_complete=0,
                         )
                    )
    self.assertEqual(e.my['present'], 1)
    
  def tearDown(self):
    restore_repo()
    

def restore_repo():
  ei.repo = ExchangeRepository()
  