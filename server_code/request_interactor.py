import anvil.server
from anvil import tables
from .requests import Request, Requests, ExchangeFormat, have_conflicts, prop_to_requests, exchange_to_save
from .exchanges import Exchange
from . import request_gateway
from . import exchange_gateway
from . import portable as port
from . import parameters as p
from . import network_interactor as ni
from . import server_misc as sm
from . import exchange_interactor as ei
from . import notifies as n
from .exceptions import InvalidRequestError
from anvil_extras.logging import TimerLogger
import time


repo = request_gateway
exchange_repo = exchange_gateway

def reset_repo():
  global repo, exchange_repo
  repo = request_gateway
  exchange_repo = exchange_gateway


def accept_pair_request(user, request_id):
  accepted_request_record = repo.RequestRecord.from_id(request_id)
  accept_request = Request.to_accept_pair_request(user.get_id(), accepted_request_record.entity)
  # port_prop = next(requests_to_props([accept_request], user))
  add_requests(user, Requests([accept_request]))


def add_requests(user, requests, link_key=""):
  """Return prop_id (None if cancelled or matching with another proposal)
  
  Side effects: Update proposal tables with additions, if valid; match if appropriate; notify
  """
  if link_key and not [invite for invite in requests.eligible_invites if invite.link_key==link_key]:
    sm.warning("add_requests requests missing {link_key} eligible_invite")
  return edit_requests(user, requests)


def edit_requests(user, requests):
  """Return prop_id (None if cancelled or matching with another proposal)
  
  Side effects: Update proposal tables with revision, if valid; match if appropriate; notify
  """
  sm.my_assert(_all_equal([r.or_group_id for r in requests]), "same or_group")
  request_editor = RequestManager(user, requests)
  request_editor.check_and_save()
  if request_editor.exchange:
    ping(user, request_editor.exchange)
  else:
    request_editor.notify_edit()
  return requests.or_group_id


def ping(user, exchange):
  user_ids = exchange.user_ids.copy()
  user_ids.remove(user.get_id())
  anvil.server.launch_background_task(
    'pings',
    user_ids=user_ids,
    start=None if exchange.start_now else exchange.start_dt,
    duration=exchange.exchange_format.duration,
  )    


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


class RequestManager:
  def __init__(self, user, requests):
    (self.user,self.requests) = (user,Requests(requests))
    self.exchange = None
    self.now = sm.now()
  
  @tables.in_transaction
  def check_and_save(self):
    self.related_prev_requests, self.unrelated_prev_requests = self._user_prev_requests()
    _check_requests_valid(self.user, self.requests, self.unrelated_prev_requests)
    other_request_records = self.potential_matching_request_records()
    _prune_request_records(other_request_records, self.now)
    exchange_prospect = self._exchange_prospect(other_request_records)
    if exchange_prospect:
      earliest_request_start_dt = exchange_prospect.start_dt
      _process_exchange_requests(exchange_prospect)
      requests_matched = [r for r in exchange_prospect if r.user!=self.requests.user]
      _cancel_other_or_group_requests(requests_matched)
      matching_request = next((r for r in exchange_prospect if r.user==self.requests.user))
      self.requests = Requests([matching_request]) # save matching request only
      self._cancel_missing_or_group_requests()
      self._save_requests()
      self.exchange = Exchange.from_exchange_prospect(exchange_prospect)
      self._save_exchange(requests_matched)
      if self.exchange.start_now and (self.now - earliest_request_start_dt).total_seconds() <= p.BUFFER_SECONDS:
        for u in self.exchange_record.users:
          u['status'] = "matched" #app_tables.users
      elif self.exchange.start_now:
        self.user['status'] = "pinging"
        for u in self.exchange_record.users:
          if u != self.user:
            u['status'] = "pinged"
    else:
      self._cancel_missing_or_group_requests()
      self._save_requests()
      if self.requests.start_now:
        self.user['status'] = "requesting"

  def _save_exchange(self, requests_matched):
    #check whether adding to pre-existing exchange
    request_records_matched = []
    for r in requests_matched:
      rr = repo.RequestRecord(r, r.request_id)
      rr.save()
      request_records_matched.append(rr)
    existing_exchange_record = exchange_repo.exchange_record_with_any_request_records(request_records_matched)
    if existing_exchange_record:
      self.exchange.exchange_id = existing_exchange_record.record_id
    self.exchange_record = exchange_repo.ExchangeRecord(self.exchange, self.exchange.exchange_id)
    self.exchange_record.save()
    self.exchange.exchange_id = self.exchange_record.record_id # for the new record case

  @property
  def requests_ids(self):
    return {r.request_id for r in self.requests}

  @property
  def or_group_ids(self):
    return {r.or_group_id for r in self.requests}

  def _user_prev_requests(self):
    user_prev_requests = list(repo.requests_by_user(self.user))
    unrelated_prev_requests = Requests([
      r for r in user_prev_requests
      if r.request_id not in self.requests_ids and r.or_group_id not in self.or_group_ids
    ])
    related_prev_requests = Requests([
      r for r in user_prev_requests
      if r.request_id in self.requests_ids or r.or_group_id in self.or_group_ids
    ])
    return related_prev_requests, unrelated_prev_requests

  def potential_matching_request_records(self):
    partial_request_dicts = [
      dict(start_now=r.start_now, start_dt=r.start_dt, exchange_format=r.exchange_format)
      for r in self.requests
    ]
    return list(repo.partially_matching_requests(self.user, partial_request_dicts, self.now, records=True))

  def _exchange_prospect(self, other_request_records):
    still_current_other_request_records = [rr for rr in other_request_records if rr.entity.current]
    other_prev_requests = current_visible_requests(self.user, still_current_other_request_records)
    return exchange_to_save(self.requests, other_prev_requests)

  def _cancel_missing_or_group_requests(self):
    requests_to_cancel = Requests([
      r for r in self.related_prev_requests
      if r.or_group_id in self.or_group_ids and r.request_id not in self.requests_ids
    ])
    for r in requests_to_cancel:
      rr = repo.RequestRecord(r, r.request_id)
      rr.cancel()
  
  def _save_requests(self):
    self.request_records = []
    for request in self.requests:
      print(f"_save_requests request_id: {request.request_id}")
      request_record = repo.RequestRecord(request, request.request_id)
      self.request_records.append(request_record)
      request_record.save()
      request.request_id = request_record.record_id

  def notify_edit(self):
    anvil.server.launch_background_task(
      'notify_edit_bg',
      user=self.user,
      requests=self.requests,
      related_prev_requests=self.related_prev_requests,
    )  


@sm.background_task_with_reporting
def notify_edit_bg(user, requests, related_prev_requests):
  new_all_eligible_users = _get_new_eligible_users(user, requests)
  old_all_eligible_users = _get_old_eligible_users(related_prev_requests)
  _notify_add(new_all_eligible_users - old_all_eligible_users, user, requests)
  if requests.times_notify_info != related_prev_requests.times_notify_info:
    _notify_edit(new_all_eligible_users & old_all_eligible_users, user, requests)
  _notify_cancel(old_all_eligible_users - new_all_eligible_users, user)


def _get_new_eligible_users(user, requests):
  try:
    (requests.user, requests.or_group_id, requests.elig_with_dict)
  except RuntimeError:
    sm.warning("notify_edit requests no common requester, or_group_id, or elig_with_dict")
  sm.my_assert(user.get_id() == requests.user, "notify_edit: user is requester")
  new_eligibility_spec = repo.eligibility_spec(requests[0])
  new_all_eligible_users = all_eligible_users(new_eligibility_spec)
  return new_all_eligible_users


def _get_old_eligible_users(related_prev_requests):
  if not related_prev_requests:
    return set()
  else:
    try:
      related_prev_requests.elig_with_dict # checks all equal
    except RuntimeError:
      sm.warning("notify_edit old requests no common elig_with_dict")
    old_r0 = related_prev_requests[0]
    old_eligibility_spec = repo.eligibility_spec(old_r0)
    return all_eligible_users(old_eligibility_spec)


def _process_exchange_requests(exchange_prospect):
  is_full = exchange_prospect.is_full
  for request in exchange_prospect:
    if is_full:
      request.current = False
    else:
      other_ep_users = set(exchange_prospect.users) - set(request.user)
      request.with_users.update(other_ep_users)


def _cancel_other_or_group_requests(requests_matched):
  request_ids = [r.request_id for r in requests_matched]
  or_group_ids = [r.or_group_id for r in requests_matched]
  for rr in repo.requests_by_or_group(or_group_ids, records=True):
    if rr.entity.request_id not in request_ids:
      rr.cancel()


def _notify_add(users, requester, requests):
  for other_user in users:
    n.notify_requests(other_user, requester, requests, f"empathy request", " has requested an empathy chat:")


def _notify_edit(users, requester, requests):
  for other_user in users:
    n.notify_requests(other_user, requester, requests, "empathy request", " has changed their empathy chat request to:")


def _notify_cancel(users, requester):
  for other_user in users:
    n.notify_requests_cancel(other_user, requester, "empathy request")


def _prune_request_records(other_request_records, now):
  for rr in other_request_records:
    if rr.entity.is_expired(now):
      rr.cancel()


def cancel_now(user, request_id=None):
  status = user['status']
  if request_id:
    request_record = repo.RequestRecord.from_id(request_id)
  else:
    request_record = now_request(user, record=True)
  request_record.cancel()
  if status == 'requesting':
    _notify_cancel(all_eligible_users(request_record.eligibility_spec), user)


def cancel_request(user, proptime_id):
  rr = repo.RequestRecord.from_id(proptime_id)
  other_or_group_requests = _other_or_group_requests(user, rr)
  if other_or_group_requests:
    _notify_edit(all_eligible_users(rr.eligibility_spec), user, other_or_group_requests)
  else:
    _notify_cancel(all_eligible_users(rr.eligibility_spec), user)
  rr.cancel()


def _other_or_group_requests(user, rr):
  user_prev_requests = list(repo.requests_by_user(user))
  return Requests([
    r for r in user_prev_requests
    if r.request_id != rr.entity.request_id and r.or_group_id == rr.entity.or_group_id
  ])


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
  if other_user in eligibility_spec['eligible_users']: # and distance < port.UNLINKED)):
    return True
  if (eligibility_spec['eligible_starred'] and ni.star_row(other_user, eligibility_spec['user'])):
    return True
  for group in eligibility_spec['eligible_groups']:
    if other_user in g.allowed_members_from_group_row(group, eligibility_spec['user']):
      return True
  if distance is None:
    distance = c.distance(eligibility_spec['user'], other_user)
  if distance <= eligibility_spec['eligible']:
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


def _all_equal(lst):
  return lst[:-1] == lst[1:] # https://stackoverflow.com/questions/3844801/check-if-all-elements-in-a-list-are-identical


def requests_to_props(requests, user):
  or_groups = [[r for r in requests if r.or_group_id == or_group_id]
                for or_group_id in {r.or_group_id for r in requests}]
  for this_or_group in or_groups:
    sm.my_assert(_all_equal([r.elig_with_dict for r in this_or_group]), "same eligibility")
    sm.my_assert(_all_equal([(r.user, r.min_size, r.max_size) for r in this_or_group]), "same proposer, sizes")
    times = []
    for r in sorted(this_or_group, key=lambda x: x.pref_order):
      sm.my_assert(not r.with_users, "no with_users")
      times.append(port.ProposalTime(
        time_id=r.request_id,
        start_now=r.start_now,
        start_date = None if r.start_now else r.start_dt,
        expire_date=r.expire_dt,
        duration=r.exchange_format.duration,
      ))
    user2 = sm.get_other_user(this_or_group[0].user)
    or_group_id = this_or_group[0].or_group_id
    yield port.Proposal(
      prop_id=or_group_id,
      user=sm.get_simple_port_user(user2, user1=user),
      own=user2==user,
      min_size=r.min_size,
      max_size=r.max_size,
      eligible=r.eligible,
      eligible_users=[sm.get_simple_port_user(sm.get_other_user(user_id), user1=user) for user_id in r.eligible_users],
      eligible_groups=r.eligible_groups,
      eligible_starred=r.eligible_starred,
      eligible_invites=r.eligible_invites,
      times=times
    )


def get_visible_requests_as_port_view_items(user):
  current_rrs = list(repo.current_requests(records=True))
  _prune_request_records(current_rrs, sm.now())
  still_current_rrs = [rr for rr in current_rrs if rr.entity.current]
  user_requests = [rr.entity for rr in still_current_rrs if rr.user == user]
  others_request_records = [rr for rr in still_current_rrs if rr.user != user]
  requests = list(current_visible_requests(user, others_request_records)) + user_requests
  port_proposals = list(requests_to_props(requests, user))
  return port.Proposal.create_view_items(port_proposals)


def now_request(user, record=False):
  current_request_records = repo.requests_by_user(user, records=True)
  for rr in current_request_records:
    if rr.entity.start_now:
      return rr if record else rr.entity
  return None


def ping_dt(exchange):
  request_records = [repo.RequestRecord.from_id(p['request_id']) for p in exchange.participants]
  return max([rr.entity.edit_dt for rr in request_records])


def confirm_wait(request_record):
  import datetime
  request_record.update_expire_dt(sm.now() + datetime.timedelta(seconds=p.WAIT_SECONDS))
