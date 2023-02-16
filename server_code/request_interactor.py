import anvil.server
from anvil import tables
import datetime
from .requests import Request, Eformat, have_conflicts, prop_to_requests, exchange_formed
from . import accounts
from . import request_gateway
from . import portable as port
from . import network_interactor as ni
from . import server_misc as sm
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
  accounts.update_default_request(port_prop, user)
  requests = tuple(prop_to_requests(port_prop))
  request_adder = RequestAdder(user, requests)
  request_adder.check_and_save()
  if request_adder.exchange:
    raise NotImplementedError("add_request -> exchange ping/notify")
    # ping other request if request_adder.exchange
    # otherwise notify invited
  return requests[0].or_group_id


class RequestAdder:
  def __init__(self, user, requests):
    self.user,self.requests = user,requests
    self.exchange = None

  @tables.in_transaction
  def check_and_save(self):
    user_id = self.user.get_id()
    #prev_requests = repo.current_requests()
    user_prev_requests = repo.requests_by_user(self.user)
    _check_requests_valid(self.user, self.requests, user_prev_requests)
    now = sm.now()
    other_request_records = potential_matching_request_records(self.requests, now)
    _prune_request_records(other_request_records, now)
    still_current_other_request_records = [rr for rr in other_request_records if rr.current]
    other_prev_requests = current_visible_requests(self.user, still_current_other_request_records)
    self.exchange = exchange_formed(self.requests, other_prev_requests)
    if self.exchange:
      # save matched request only* and resulting exchange
      # *cancel other or_group requests before saving (or just don't save them)
      # update status
      raise NotImplementedError("add_request -> exchange")
    else:
      _save_new_requests(self.requests)


def _prune_request_records(other_request_records, now):
  for rr in other_request_records:
    if rr.expired(now):
      rr.cancel()


def potential_matching_request_records(requests, now):
  partial_request_dicts = [
    dict(start_now=r.start_now, start_dt=r.start_dt, eformat=r.eformat)
    for r in requests
  ]
  return repo.partially_matching_requests(partial_request_dicts, now, records=True)


def current_visible_requests(user, request_records=None):
  from . import connections as c
  user_id = user.get_id()
  if request_records == None:
    request_records = [rr for rr in repo.current_requests(records=True) if rr.user != user]
  # group_memberships = 
  # starred_by_list =
  all_requesters = {rr.user for rr in request_records}
  # max_eligible_dict = {user_id: max((r.eligible for r in all_requests if r.user=user_id))
  #                      for user_id in all_requester_ids}
  distances = c.distances(all_requesters, user)
  out_requests = []
  for rr in request_records:
    if is_eligible(rr.eligibility_spec, user, distances[rr.user]) and rr.entity.has_room_for(user_id):
      out_requests.append(rr.entity)
  return out_requests


def is_eligible(eligibility_spec, other_user, distance=None):
  from . import connections as c
  from . import groups_server as g
  if distance is None:
    distance = c.distance(eligibility_spec['user'], other_user)
  if (distance <= eligibility_spec['eligible'] or other_user in eligibility_spec['eligible_users']):# and distance < port.UNLINKED)):
    return True
  elif (eligibility_spec['eligible_starred'] and ni.star_row(other_user, eligibility_spec['user'])):
    return True
  else:
    for group in eligibility_spec['eligible_groups']:
      if other_user in g.allowed_members_from_group_row(group, eligibility_spec['user']):
        return True
    return False


def all_eligible_users(eligibility_spec):
  from . import connections as c
  from . import groups_server as g
  user = eligibility_spec['user']
  all_eligible = set()
  if eligibility_spec['eligible']:
    all_eligible.update(set(c.get_connected_users(user, up_to_degree=eligibility_spec['eligible'])))
  if eligibility_spec['eligible_starred']:
    all_eligible.update(set(ni.starred_users(user)))
  if eligibility_spec['eligible_users']:
    all_eligible.update(set(eligibility_spec['eligible_users']))
  for group in eligibility_spec['eligible_groups']:
    all_eligible.update(set(g.allowed_members_from_group_row(group, user))-{user})
  return all_eligible


def _check_requests_valid(user, requests, user_prev_requests):
  if user['trust_level'] < 3:
    for request in requests:
      if request.eligible > 2:
        raise InvalidRequestError("Not allowed to invite beyond 2nd degree links")
      # also check eligibility to invite specific users and groups?
  if have_conflicts(list(requests) + list(user_prev_requests)):
    raise InvalidRequestError("New requests have a time conflict with your existing requests.")
  # also check for current/upcoming exchange conflicts...
  # ...by pulling in requests associated with upcoming exchanges to have_conflicts() call


def _save_new_requests(requests):
  for request in requests:
    new_request_record = repo.RequestRecord(request)
    new_request_record.save()
    request.request_id = new_request_record.record_id


def _cancel_request(user, proptime_id):
  raise NotImplementedError("_cancel_request")
  # proptime = ProposalTime.get_by_id(proptime_id)
  # if proptime:
  #   proptime.cancel_this(user)
