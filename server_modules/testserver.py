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
def test_add_user(em, level = 1, r_em = False, m_em = False):
  new_user = app_tables.users.add_row(email=em,
                                      enabled=True,
                                      trust_level=level,
                                      request_em=r_em,
                                      match_em = m_em
                                     )
  return new_user.get_id()


@anvil.server.callable
@anvil.tables.in_transaction
def test_add_request(user_id, request_type = "offering"):
  user = app_tables.users.get_by_id(user_id)
  now = datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc())
  new_row = app_tables.requests.add_row(user=user,
                                        current=True,
                                        request_type=request_type,
                                        start=now,
                                        last_confirmed=now,
                                        cancelled_matches=0
                                       )
  return new_row