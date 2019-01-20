import anvil.google.auth, anvil.google.drive, anvil.google.mail
from anvil.google.drive import app_files
import anvil.email
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.users
import anvil.server
import datetime

@anvil.server.callable
@anvil.tables.in_transaction
def add_user(email):
  pass

@anvil.server.callable
@anvil.tables.in_transaction
def add_request(email, level = 1, r_em = False, m_em = False):
  pass