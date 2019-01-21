import anvil.google.auth, anvil.google.drive, anvil.google.mail
from anvil.google.drive import app_files
import anvil.email
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.users
import anvil.server
import parameters as p
import matcher
import datetime


@anvil.server.callable
@anvil.tables.in_transaction
def test_add_user(em, level = 1, r_em = False, m_em = False):
  assert anvil.server.session['user']['trust_level'] >= p.TEST_TRUST_LEVEL
  if not anvil.server.session['test_record']:
    anvil.server.session['test_record'] = create_tests_record()
  new_user = app_tables.users.add_row(email=em,
                                      enabled=True,
                                      trust_level=level,
                                      request_em=r_em,
                                      match_em = m_em
                                     )
  test_users = anvil.server.session['test_record']['test_users']
  anvil.server.session['test_record']['test_users'] = test_users + [new_user]
  return new_user.get_id()


@anvil.server.callable
@anvil.tables.in_transaction
def test_add_request(user_id, request_type = "offering"):
  assert anvil.server.session['user']['trust_level'] >= p.TEST_TRUST_LEVEL
  if not anvil.server.session['test_record']:
    anvil.server.session['test_record'] = create_tests_record()
  user = app_tables.users.get_by_id(user_id)
  #now = datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc())
  #new_row = app_tables.requests.add_row(user=user,
  #                                      current=True,
  #                                      request_type=request_type,
  #                                      start=now,
  #                                      last_confirmed=now,
  #                                      cancelled_matches=0
  #                                     )
  jitsi_code = None
  last_confirmed = None
  num_emailed = 0
  alt_avail = None
  if request_type=="offering":
    requests = [r for r in app_tables.requests.search(current=True,
                                                      match_id=None)]
  else: 
    assert request_type=="requesting"
    requests = [r for r in app_tables.requests.search(current=True,
                                                      request_type="offering",
                                                      match_id=None)]    
  now = datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc())
  new_row = app_tables.requests.add_row(user=user,
                                        current=True,
                                        request_type=request_type,
                                        start=now,
                                        last_confirmed=now,
                                        cancelled_matches=0
                                       )
  current_row = new_row
  if requests:
    jitsi_code = matcher.new_jitsi_code()
    current_row['match_id'] = matcher.new_match_id()
    current_row['jitsi_code'] = jitsi_code
    cms = [r['cancelled_matches'] for r in requests]
    eligible_requests = [r for r in requests if r['cancelled_matches']==min(cms)]
    earliest_request = min(eligible_requests, key=lambda row: row['start'])
    earliest_request['match_id'] = current_row['match_id']
    earliest_request['jitsi_code'] = jitsi_code
    last_confirmed = earliest_request['last_confirmed']
    alt_avail = len(requests) > 1
  #else:
  #  num_emailed = request_emails(request_type)
  #####
  test_requests = anvil.server.session['test_record']['test_requests']
  anvil.server.session['test_record']['test_requests'] = test_requests + [new_row]
  return new_row


def create_tests_record():
  return app_tables.test_data.add_row(test_users = [],
                                      test_requests = []
                                     )


@anvil.server.callable
@anvil.tables.in_transaction
def test_clear():
  assert anvil.server.session['user']['trust_level'] >= p.TEST_TRUST_LEVEL
  test_records = app_tables.test_data.search()
  for row in test_records:  
    for user in row['test_users']:
      user.delete()
    for request in row['test_requests']:
      request.delete()                              
    row.delete()
  anvil.server.session['test_record'] = None
    

@anvil.server.callable
def test_get_user_list():
  assert anvil.server.session['user']['trust_level'] >= p.TEST_TRUST_LEVEL
  users = app_tables.users.search()
  to_return = []
  for user in users:
    to_return += [(user['email'], user.get_id())]
  return to_return