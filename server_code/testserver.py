from anvil.tables import app_tables
import anvil.server
from . import server_misc as sm
from . import matcher


@anvil.server.callable
@anvil.tables.in_transaction
def test_add_user(em, level=1, r_em=False, p_em=False):
  print("test_add_user", em, level, r_em, p_em)
  assert anvil.server.session['trust_level'] >= matcher.TEST_TRUST_LEVEL
  if not anvil.server.session['test_record']:
    anvil.server.session['test_record'] = create_tests_record()
  new_user = app_tables.users.add_row(email=em,
                                      name = em,
                                      enabled=True,
                                      trust_level=level,
                                      request_em=r_em,
                                      pinged_em = p_em
                                     )
  test_users = anvil.server.session['test_record']['test_users']
  anvil.server.session['test_record']['test_users'] = test_users + [new_user]
  return new_user.get_id()


@anvil.server.callable
@anvil.tables.in_transaction
def test_add_request(user_id, proposal):
  print("test_add_request", user_id, proposal)
  assert anvil.server.session['trust_level'] >= matcher.TEST_TRUST_LEVEL
  if not anvil.server.session['test_record']:
    anvil.server.session['test_record'] = create_tests_record()
  user = app_tables.users.get_by_id(user_id)
  state = matcher._add_proposal(user, proposal)
  
  test_proposals = anvil.server.session['test_record']['test_proposals']
  new_row = app_tables.proposals.get_by_id(proposal.prop_id)
  if new_row: 
    anvil.server.session['test_record']['test_requests'] = test_proposals + [new_row]
    test_times = anvil.server.session['test_record']['test_times']
    anvil.server.session['test_record']['test_times'] = test_times + list(app_tables.proposal_times.search(proposal=new_row))
  return new_row


def create_tests_record():
  return app_tables.test_data.add_row(test_users = [],
                                      test_proposals = [],
                                      test_times = [],
                                     )


@anvil.server.callable
def accept_now_proposal(user_id):
  assert anvil.server.session['trust_level'] >= matcher.TEST_TRUST_LEVEL
  tester = sm.get_user()
  tester_now_proposal = matcher.get_now_proposal_time(tester)
  if tester_now_proposal:
    matcher.accept_proposal(tester_now_proposal.get_id(), user_id)


@anvil.server.callable
@anvil.tables.in_transaction
def test_clear():
  print("('test_clear')")
  assert anvil.server.session['trust_level'] >= matcher.TEST_TRUST_LEVEL
  test_records = app_tables.test_data.search()
  test_matches = set()
  for row in test_records:
    for user in row['test_users']:
      user.delete()
    for time in row['test_times']:
      test_matches.add(app_tables.matches.get(proposal_time=time))
      time.delete()
    for proposal in row['test_proposals']:
      proposal.delete()
    row.delete()
    for match in test_matches:
      if match is not None:
        for row in app_tables.chat.search(match=match):
          row.delete()
        match.delete()
  anvil.server.session['test_record'] = None


@anvil.server.callable
def test_get_user_list():
  print("('test_get_user_list')")
  assert anvil.server.session['trust_level'] >= matcher.TEST_TRUST_LEVEL
  users = app_tables.users.search()
  to_return = []
  for user in users:
    to_return += [(user['email'], user.get_id())]
  return to_return
