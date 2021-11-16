import anvil.users
from anvil.tables import app_tables
import anvil.server
from . import server_misc as sm
from .server_misc import authenticated_callable
from . import matcher
from . import portable


@authenticated_callable
@anvil.tables.in_transaction
def test_add_user(em, level=1, r_em=False, p_sms=True):
  print("test_add_user", em, level, r_em, p_sms)
  if anvil.server.session['trust_level'] >= sm.TEST_TRUST_LEVEL:
    if not anvil.server.session['test_record']:
      anvil.server.session['test_record'] = create_tests_record()
    new_user = app_tables.users.add_row(email=em,
                                        first_name = em,
                                        enabled=True,
                                        trust_level=level,
                                        request_em=r_em,
                                        pinged_sms = p_sms
                                       )
    test_users = anvil.server.session['test_record']['test_users']
    anvil.server.session['test_record']['test_users'] = test_users + [new_user]
    return new_user.get_id()


@authenticated_callable
@anvil.tables.in_transaction
def test_add_request(user_id, port_prop):
  print("test_add_request", user_id)
  if anvil.server.session['trust_level'] >= sm.TEST_TRUST_LEVEL:
    user = app_tables.users.get_by_id(user_id)
    state, prop_id = matcher._add_proposal(user, port_prop)
    new_prop = matcher.Proposal.get_by_id(prop_id)
    if new_prop: 
      _add_prop_row_to_test_record(new_prop._row)


def create_tests_record():
  return app_tables.test_data.add_row(test_users = [],
                                      test_proposals = [],
                                      test_times = [],
                                     )


@authenticated_callable
def add_now_proposal():
  print("add_now_proposal")
  if anvil.server.session['trust_level'] >= sm.TEST_TRUST_LEVEL:
    tester = sm.get_user()
    anvil.server.call('add_proposal', portable.Proposal(), tester.get_id())
    tester_now_proptime = matcher.ProposalTime.get_now_proposing(tester)
    if tester_now_proptime:
      _add_prop_row_to_test_record(tester_now_proptime.proposal._row)
    

@authenticated_callable
def accept_now_proposal(user_id):
  print("accept_now_proposal", user_id)
  if anvil.server.session['trust_level'] >= sm.TEST_TRUST_LEVEL:
    tester = sm.get_user()
    tester_now_proptime = matcher.ProposalTime.get_now_proposing(tester)
    if tester_now_proptime:
      state = matcher.accept_proposal(tester_now_proptime.get_id(), user_id)
      if state['status'] in ['pinging', 'matched']:
        _add_prop_row_to_test_record(tester_now_proptime.proposal._row)

    
def _add_prop_row_to_test_record(prop_row):
  print("_add_prop_row_to_test_record", prop_row['created'])
  if not anvil.server.session['test_record']:
    anvil.server.session['test_record'] = create_tests_record()
  test_proposals = anvil.server.session['test_record']['test_proposals']
  if prop_row not in test_proposals:
    anvil.server.session['test_record']['test_proposals'] = test_proposals + [prop_row]
    test_times = anvil.server.session['test_record']['test_times']
    proptimes = matcher.ProposalTime.times_from_proposal(matcher.Proposal(prop_row))
    anvil.server.session['test_record']['test_times'] = test_times + [proptime._row 
                                                                      for proptime in proptimes]
 

@authenticated_callable
@anvil.tables.in_transaction
def test_clear():
  print("('test_clear')")
  if anvil.server.session['trust_level'] >= sm.TEST_TRUST_LEVEL:
    test_records = app_tables.test_data.search()
    test_matches = set()
    for test_row in test_records:
      for user in test_row['test_users']:
        user.delete()
      for time in test_row['test_times']:
        print("time", time['expire_date'])
        test_matches.add(app_tables.matches.get(proposal_time=time))
        time.delete()
      for proposal in set(test_row['test_proposals']):
        print("proposal", proposal['created'])
        proposal.delete()
      test_row.delete()
    for match in test_matches:
      if match is not None:
        print("match", match['match_commence'])
        for chat_row in app_tables.chat.search(match=match):
          chat_row.delete()
        match.delete()
    anvil.server.session['test_record'] = None


@authenticated_callable
def test_get_user_list():
  print("('test_get_user_list')")
  if anvil.server.session['trust_level'] >= sm.TEST_TRUST_LEVEL:
    users = app_tables.users.search()
    to_return = []
    for user in users:
      to_return += [(user['email'], user.get_id())]
    return to_return
