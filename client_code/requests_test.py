import anvil.server
import anvil.users
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import unittest
from . import helper as h
from . import requests as r


class MyRequestTest(unittest.TestCase):
  def test_start(self):
    my_request = r.MyRequest(start_now=False, start_dt=h.now())
    self.assertTrue(my_request.get_errors()) #, 
#                      {'start_date': ("The Start Time must be at least " 
#                           + str(CANCEL_MIN_MINUTES) + " minutes away.")}
#                     )
