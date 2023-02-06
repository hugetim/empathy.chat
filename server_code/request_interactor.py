import anvil.server
from anvil import tables
import datetime
from .requests import Request, Eformat, have_conflicts, prop_to_requests, exchange_formed
from . import accounts
from . import request_gateway
from .exceptions import InvalidRequestError


def reset_repo():
  global repo
  repo = request_gateway


repo = None
reset_repo()


def _add_request(user, port_prop, link_key=""):
  """Return prop_id (None if cancelled or matching with another proposal)
  
  Side effects: Update proposal tables with additions, if valid; match if appropriate; notify
  """
  user_id = user.get_id()
  accounts.update_default_request(port_prop, user)
  requests = tuple(prop_to_requests(port_prop))
  prev_requests = repo.current_requests()
  user_prev_requests = [r for r in prev_requests if r.user.user_id == user_id]
  # confirm validity
  if have_conflicts(list(requests) + list(user_prev_requests)):
    raise InvalidRequestError("New requests have a time conflict with your existing requests.")
  # also check for current/upcoming exchange conflicts...
  # ...by pulling in requests associated with upcoming exchanges to have_conflicts() call
    
  # check for previous requests that match with one of these
  other_prev_requests = [r for r in prev_requests if r.user.user_id != user_id]
  _exchange = exchange_formed(requests, other_prev_requests)
  if _exchange:
    # drop other or_group requests before saving
    # save matched request and resulting exchange
    # update status
    # trigger ping if needed
    pass
  else:
    _save_new_requests(requests)
  # ping other request if match
  # otherwise notify invited
  return requests[0].or_group_id


def _check_valid_requests(requests):
  pass
      # if user['trust_level'] < 3:
      # new_prop_row['eligible'] = min(2, new_prop_row['eligible'])


@tables.in_transaction(relaxed=True)
def _save_new_requests(requests):
  for request in requests:
    new_request_record = repo.RequestRecord(request)
    new_request_record.save()
    request.request_id = new_request_record.record_id
