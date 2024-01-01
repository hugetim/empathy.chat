import anvil.users
import anvil.tables
from anvil.tables import app_tables
import anvil.server
import anvil.secrets as secrets
from . import server_misc as sm
from . import accounts
from .server_misc import authenticated_callable
from . import matcher
from . import request_interactor as ri
from . import portable


@authenticated_callable
def get_test_user_id():
  if anvil.users.get_user()['trust_level'] >= sm.TEST_TRUST_LEVEL:
    test_user = app_tables.users.get(email=secrets.get_secret('test_user_email'))
    return test_user.get_id()


@authenticated_callable
def add_now_proposal_old():
  print("add_now_proposal")
  if anvil.users.get_user()['trust_level'] >= sm.TEST_TRUST_LEVEL:
    tester = sm.get_acting_user()
    anvil.server.call('add_proposal', portable.Proposal(times=[portable.ProposalTime(start_now=True)], eligible=1), user_id=tester.get_id())
    matcher.propagate_update_needed()
    # tester_now_proptime = ri.now_request(tester)  #matcher.ProposalTime.get_now_proposing(tester)
    # if tester_now_proptime:
    #   _add_prop_row_to_test_record(tester_now_proptime.proposal._row)
    

@authenticated_callable
def accept_now_proposal_old(user_id):
  print("accept_now_proposal", user_id)
  if anvil.users.get_user()['trust_level'] >= sm.TEST_TRUST_LEVEL:
    tester = sm.get_acting_user()
    tester_now_request = ri.now_request(tester)
    if tester_now_request:
      state = matcher.accept_proposal(tester_now_request.request_id, user_id=user_id)
      matcher.propagate_update_needed()
      # if state['status'] in ['pinging', 'matched']:
      #   _add_prop_row_to_test_record(tester_now_proptime.proposal._row)

    
# def _add_prop_row_to_test_record(prop_row):
#   print("_add_prop_row_to_test_record", prop_row['created'])
#   if not anvil.server.session.get('test_record'):
#     anvil.server.session['test_record'] = create_tests_record()
#   test_proposals = anvil.server.session['test_record']['test_proposals']
#   if prop_row not in test_proposals:
#     anvil.server.session['test_record']['test_proposals'] = test_proposals + [prop_row]
#     test_times = anvil.server.session['test_record']['test_times']
#     proptimes = proposals.ProposalTime.times_from_proposal(proposals.Proposal(prop_row))
#     anvil.server.session['test_record']['test_times'] = test_times + [proptime._row 
#                                                                       for proptime in proptimes]


# def create_tests_record():
#   return app_tables.test_data.add_row(test_users = [],
#                                       test_proposals = [],
#                                       test_times = [],
#                                      )
  