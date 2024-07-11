import anvil.server
from auto_batch import tables
from .requests import Request, Requests, ExchangeFormat, ExchangeProspect, have_conflicts, prop_to_requests, selected_exchange
from .exchanges import Exchange
from .relationship import Relationship
from . import request_gateway
from . import exchange_gateway
from . import portable as port
from . import parameters as p
from . import server_misc as sm
from . import exchange_interactor as ei
from . import connections as c
from . import notifies as n
from . import helper as h
from .exceptions import InvalidRequestError
from anvil_extras.logging import TimerLogger
import time
from copy import deepcopy


repo = request_gateway
exchange_repo = exchange_gateway

def reset_repo():
  global repo, exchange_repo
  repo = request_gateway
  exchange_repo = exchange_gateway


def accept_almost_full_request(user, request_id, user_ids_accepting):
  accepted_request_record = repo.RequestRecord.from_id(request_id)
  accept_request = Request.to_accept_almost_full_request(user.get_id(), accepted_request_record.entity, user_ids_accepting)
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
  sm.my_assert(h.all_equal([r.or_group_id for r in requests]), "same or_group")
  request_editor = RequestManager()
  _pre_fetch_relevant_rows(requests, user, request_editor.now)
  request_editor.check_and_save(user, requests)
  if request_editor.exchange:
    ei.ping(user, request_editor.exchange)
  else:
    request_editor.notify_edit()
  return requests.or_group_id


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


def _pre_fetch_relevant_rows(requests, user, now):
  repo.get_user_row_by_id(requests.user)
  for request in requests:
    repo.get_exchange_format_row(request.exchange_format) # to initialize relevant cache pre-transaction
    out = {}
    out['with_users'] = [repo.get_user_row_by_id(user_id)
                        for user_id in request.with_users]
    out['eligible_users'] = [repo.get_user_row_by_id(user_id)
                            for user_id in request.eligible_users]
    out['eligible_groups'] = [repo.get_group_row_by_id(port_group.group_id)
                              for port_group in request.eligible_groups]
    out['eligible_invites'] = [repo.get_invite_row_by_id(port_invite.invite_id)
                              for port_invite in request.eligible_invites]
  other_request_records, related_prev, unrelated_prev = _relevant_request_records(requests, user, now)
  _prune_request_records(other_request_records, now)
  current_visible_requests(user, other_request_records)


class RequestManager:
  def __init__(self):
    self.now = sm.now()

  def _init_check_and_save(self, user):
    user.update()
    self._user = user
    self._user_id = user.get_id()
    self.exchange = None

  def _load_relevant_request_records(self, requests):
    self._other_request_records, self._related_prev_request_records, self._unrelated_prev_requests = (
      _relevant_request_records(requests, self._user, self.now)
    )
    self._related_prev_requests = Requests([rr.entity for rr in self._related_prev_request_records])
  
  @tables.in_transaction
  def check_and_save(self, user, requests):
    with TimerLogger("check_and_save", format="{name}: {elapsed:6.3f} s | {msg}") as timer:
      self._init_check_and_save(user)
      requests = Requests(deepcopy(requests))
      self._load_relevant_request_records(requests)
      timer.check("_load_relevant_request_records")
      _check_requests_valid(self._user, requests, self._unrelated_prev_requests)
      _prune_request_records(self._other_request_records, self.now)
      timer.check("_prune_request_records")
      exchange_prospects = _potential_matches(self._user, requests, self._other_request_records)
      has_enough_exchanges = [ep for ep in exchange_prospects if ep.has_enough]
      timer.check("exchange_prospects")
      if has_enough_exchanges:
        exchange_to_be = selected_exchange(has_enough_exchanges)
        _process_exchange_requests(exchange_to_be)
        requests_matched = exchange_to_be.their_requests(self._user_id)
        _cancel_other_or_group_requests(requests_matched)
        timer.check("_cancel_other_or_group_requests")
        requests = Requests([exchange_to_be.my_request(self._user_id)]) # save matching request only
        _cancel_missing_or_group_requests(requests, self._related_prev_request_records)
        self._save_requests(requests)
        timer.check("_save_requests")
        self._save_exchange(exchange_to_be)
        timer.check("_save_exchange")
        self._update_exchange_user_statuses()
      else:
        _cancel_missing_or_group_requests(requests, self._related_prev_request_records)
        timer.check("_cancel_missing_or_group_requests")
        self._save_requests(requests)
        timer.check("_save_requests")
        self._save_exchange_prospects(exchange_prospects)
        timer.check("_save_exchange_prospects")
        if requests.start_now:
          self._user['status'] = "requesting"
      self._requests = requests
  
  def _save_exchange(self, exchange_to_be):
    self.exchange = Exchange.from_exchange_prospect(exchange_to_be, self.now)
    with TimerLogger("  _save_exchange", format="{name}: {elapsed:6.3f} s | {msg}") as timer:
      their_request_ids = exchange_to_be.their_requests(self._user_id).request_ids
      request_records_matched = [rr for rr in self._other_request_records if rr.record_id in their_request_ids]
      for rr in request_records_matched:
        rr.entity = next((r for r in exchange_to_be if r.request_id == rr.record_id))
        rr.save()
      repo.cache_request_record_rows(request_records_matched)
      timer.check("  requests_matched saved")
      existing_exchange_record = exchange_repo.exchange_record_with_any_request_records(request_records_matched)
      timer.check("  exchange_record_with_any_request_records")
      if existing_exchange_record:
        self.exchange.exchange_id = existing_exchange_record.record_id
      self._exchange_record = exchange_repo.ExchangeRecord(self.exchange, self.exchange.exchange_id)
      self._exchange_record.save()
      self.exchange.exchange_id = self._exchange_record.record_id # for the new record case
  
  def _save_requests(self, requests):
    for request in requests:
      #print(f"_save_requests request_id: {request.request_id}")
      matching_prev_records = [rr for rr in self._related_prev_request_records if rr.record_id == request.request_id]
      if matching_prev_records:
        request_record = matching_prev_records[0]
        request.create_dt = request_record.entity.create_dt
        request.with_users = request.with_users if request.with_users else request_record.entity.with_users
        request_record.entity = request
      else:
        request_record = repo.RequestRecord(request, request.request_id)
      request_record.save()
      request.request_id = request_record.record_id
      repo.cache_request_record_rows([request_record])

  def _save_exchange_prospects(self, exchange_prospects):
    repo.clear_eprs_for_rrs(self._related_prev_request_records)
    for ep in exchange_prospects:
      repo.ExchangeProspectRecord(ep).save()
  
  def _update_exchange_user_statuses(self):
    if self.exchange.start_now:
      users = self._exchange_record.users
      entered_user_ids = self.exchange.currently_matched_user_ids
      if entered_user_ids:
        with tables.batch_update:
          for u in users:
            if u.get_id() in entered_user_ids:
              u['status'] = "matched"
      else:
        with tables.batch_update:
          self._user['status'] = "pinging"
          for u in users:
            if u != self._user:
              u['status'] = "pinged"
  
  def notify_edit(self):
    anvil.server.launch_background_task(
      'notify_edit_bg',
      user=self._user,
      requests=self._requests,
      related_prev_requests=self._related_prev_requests,
    )  


def _requests_ids(requests):
  return {r.request_id for r in requests}, {r.or_group_id for r in requests}


def _cancel_missing_or_group_requests(requests, related_prev_request_records):
  requests_ids, or_group_ids = _requests_ids(requests)
  for rr in related_prev_request_records:
    if rr.entity.or_group_id in or_group_ids and rr.entity.request_id not in requests_ids:
      rr.cancel()


def _relevant_request_records(requests, user, now):
  partial_request_dicts = [
    dict(start_now=r.start_now, start_dt=r.start_dt, exchange_format=r.exchange_format)
    for r in requests
  ]
  retrieved = list(repo.user_and_partially_matching_requests(user, partial_request_dicts, now, records=True))
  other_request_records = [rr for rr in retrieved if rr.user != user]
  user_prev_request_records = [rr for rr in retrieved if rr.user == user]
  requests_ids, or_group_ids = _requests_ids(requests)
  unrelated_prev_requests = Requests([
    rr.entity for rr in user_prev_request_records
    if rr.entity.request_id not in requests_ids and rr.entity.or_group_id not in or_group_ids
  ])
  related_prev_request_records = [
    rr for rr in user_prev_request_records
    if rr.entity.request_id in requests_ids or rr.entity.or_group_id in or_group_ids
  ]
  return other_request_records, related_prev_request_records, unrelated_prev_requests


def _potential_matches(user, requests, other_request_records):
  still_current_other_request_records = [rr for rr in other_request_records if rr.entity.current]
  other_exchange_prospect_records = repo.request_records_prospects(still_current_other_request_records, records=True)
  other_exchange_prospects = (
    [epr.entity for epr in other_exchange_prospect_records] 
    + [ExchangeProspect([rr.entity]) for rr in still_current_other_request_records]
  )
  return get_new_prospects(user, requests, still_current_other_request_records, other_exchange_prospects)


def _process_exchange_requests(exchange_prospect):
  is_full = exchange_prospect.is_full
  for request in exchange_prospect:
    if is_full:
      request.current = False
    else:
      other_ep_users = set(exchange_prospect.users) - set(request.user + request.with_users)
      request.with_users.extend(other_ep_users)


def _cancel_other_or_group_requests(requests_matched):
  request_ids = [r.request_id for r in requests_matched]
  or_group_ids = [r.or_group_id for r in requests_matched]
  for rr in repo.requests_by_or_group(or_group_ids, records=True):
    if rr.entity.request_id not in request_ids:
      rr.cancel()


def _prune_request_records(other_request_records, now):
  for rr in other_request_records:
    if rr.entity.is_expired(now):
      rr.cancel()


def confirm_wait(request_record):
  import datetime
  request_record.update_expire_dt(sm.now() + datetime.timedelta(seconds=p.WAIT_SECONDS))


def now_request(user, record=False):
  current_request_records = repo.requests_by_user(user, records=True)
  for rr in current_request_records:
    if rr.entity.start_now:
      return rr if record else rr.entity
  return None


def cancel_now(user, request_id=None):
  manager = CancelManager()
  manager.cancel_now(user, request_id)
  if manager.user_orig_status == 'requesting': # as opposed to 'pinging'
    rr = manager.request_record
    _notify_cancel(all_eligible_users(rr.entity, rr.eligibility_spec), user)


class CancelManager:
  @tables.in_transaction
  def cancel_now(self, user, request_id):
    user.update()
    self.user_orig_status = user['status']
    if request_id:
      request_record = repo.RequestRecord.from_id(request_id)
    else:
      request_record = now_request(user, record=True)
    if request_record and request_record.entity.current:
      request_record.cancel()
    self.request_record = request_record


def cancel_request(user, request_id):
  rr = repo.RequestRecord.from_id(request_id)
  other_or_group_requests = _other_or_group_requests(user, rr)
  if other_or_group_requests:
    _notify_edit(all_eligible_users(rr.entity, rr.eligibility_spec), user, other_or_group_requests.notify_info)
  else:
    _notify_cancel(all_eligible_users(rr.entity, rr.eligibility_spec), user)
  rr.cancel_in_transaction()


def _other_or_group_requests(user, rr):
  user_prev_requests = list(repo.requests_by_user(user))
  return Requests([
    r for r in user_prev_requests
    if r.request_id != rr.entity.request_id and r.or_group_id == rr.entity.or_group_id
  ])


def relationships(other_users, user):
  from . import groups_server as g
  distances = c.distances(other_users, user)
  group_relationships = g.group_relationships(other_users, user)
  return {u: Relationship(distance=distances[u],
                          min_trust_level=min(user['trust_level'], u['trust_level']),
                          **group_relationships[u],
                         )
          for u in other_users}


def _get_new_prospects(exchange_prospect, new_requests, distances):
  new_exchange_prospects = []
  for new_request in new_requests:
    new_exchange_prospects.extend(new_request.get_prospects([exchange_prospect], distances))
  return new_exchange_prospects


def get_new_prospects(user, requests, other_request_records, other_exchange_prospects):
  user_id = user.get_id()
  all_requesters = {rr.user for rr in other_request_records}
  other_request_especs = {rr.record_id: rr.eligibility_spec for rr in other_request_records}
  other_users = {u.get_id(): u for u in all_requesters}
  rels = relationships(all_requesters, user)
  requests_eligibility_spec = repo.eligibility_spec(requests[0], user)
  out = []
  for ep in other_exchange_prospects:
    ep_rels = _extend_relationships(rels, ep.distances)
    if _prospect_mutually_eligible(user, requests[0], requests_eligibility_spec, ep_rels, ep, other_request_especs, other_users):
      new_ep_distances = _distances_update(ep.distances, ep_rels, user_id)
      out.extend(_get_new_prospects(ep, requests, new_ep_distances))
  return out


def _distances_update(old_distances, ep_rels, user_id):
  _ep_rels = {u.get_id(): ep_rels[u] for u in ep_rels.keys()}
  out = {user_id: {u_id: _ep_rels[u_id].distance for u_id in old_distances}}
  for u_id in old_distances:
    if u_id != user_id:
      out[u_id] = old_distances[u_id].copy()
      out[u_id][user_id] = _ep_rels[u_id].distance
  return out


def current_visible_requests(user, request_records):
  return [ep[0] for ep in current_visible_prospects(user, [], request_records)]


def current_visible_prospects(user, exchange_prospects, request_records):
  if not request_records:
    return []
  all_requesters = {rr.user for rr in request_records}
  rels = relationships(all_requesters, user)
  single_exchange_prospects = [ExchangeProspect([rr.entity], temp=True) for rr in request_records if not _request_in_eps(rr.entity, exchange_prospects)]
  out_prospects = []
  for ep in (exchange_prospects + single_exchange_prospects):
    ep_request_records = [rr for rr in request_records if rr.entity in ep]
    print([repr(key) for key in rels])
    ep_rels = {rr.user: rels[rr.user] for rr in ep_request_records}
    if is_eligible_for_prospect(user, ep, ep_rels, ep_request_records):
      out_prospects.append(ep)
  return out_prospects


def _prospect_mutually_eligible(user, rep_request, requests_eligibility_spec, rels, ep, other_request_especs, other_users):
  new_ep = ExchangeProspect(list(ep.requests)+[rep_request], temp=True)
  for other_request in ep:
    other_user = other_users.get(other_request.user, repo.get_user_row_by_id(other_request.user))
    rel = rels[other_user]
    if not is_eligible(new_ep, other_user, rel, requests_eligibility_spec):
      return False
    eligibility_spec = other_request_especs.get(other_request.request_id, repo.eligibility_spec(other_request))
    if not is_eligible(new_ep, user, rel, eligibility_spec):
      return False
  return True


def is_eligible_for_prospect(user, ep, rels, request_records):
  other_users = [rr.user for rr in request_records]
  # rels = relationships(other_users, user)
  ep_rels = _extend_relationships(rels, ep.distances)
  for request in ep:
    other_user = next((u for u in other_users if u.get_id() == request.user))
    rel = ep_rels[other_user]
    eligibility_spec = next((rr.eligibility_spec for rr in request_records if rr.user == other_user))
    if not is_eligible(ep, user, rel, eligibility_spec):
      return False
  return True


def _extend_relationships(rels, ep_distances):
  pair_eligible_distances = {u.get_id(): rels[u].distance for u in rels.keys() if rels[u].pair_eligible}
  if pair_eligible_distances:
    return {u: _new_rel(u.get_id(), rels[u], pair_eligible_distances, ep_distances) for u in rels.keys()}
  else:
    return rels


def _new_rel(other_user_id, rel, pair_eligible_distances, ep_distances):
  alt_distances = [pair_eligible_distances[u_id] + ep_distances[u_id][other_user_id]
                   for u_id in pair_eligible_distances.keys()
                   if ep_distances and u_id in ep_distances.keys() and other_user_id in ep_distances[u_id].keys()]
  if alt_distances:
    return rel.update_distance(min(rel.distance, *alt_distances))
  else:
    return rel


def is_eligible(request, other_user, rel, eligibility_spec):
  included = is_included(eligibility_spec, other_user, rel.distance)
  return _is_eligible(request, other_user, rel, included)


def _is_eligible(request, other_user, rel, included):
  return (
    (rel.pair_eligible or (request.max_size >= 3 and rel.eligible))
    and included
    and request.has_room_for(other_user.get_id())
  )

def is_included(eligibility_spec, other_user, distance=None):
  from . import groups_server as g
  if eligibility_spec['eligible_all']:
    return True
  if other_user in eligibility_spec['eligible_users']:
    return True
  if (eligibility_spec['eligible_starred'] and repo.star_row(other_user, eligibility_spec['user'])):
    return True
  for group in eligibility_spec['eligible_groups']:
    if other_user in g.allowed_members_from_group_row(group, eligibility_spec['user']):
      return True
  if eligibility_spec['eligible'] and distance is None:
    distance = c.distance(eligibility_spec['user'], other_user)
  if eligibility_spec['eligible'] and distance <= eligibility_spec['eligible']:
    return True
  return False


def _all_included_users(eligibility_spec):
  from . import groups_server as g
  user = eligibility_spec['user']
  all_eligible = set()
  if eligibility_spec['eligible_all']:
    all_eligible.update(set(c.get_connected_users(user, up_to_degree=Relationship.MAX_PAIR_ELIGIBLE_DISTANCE)))
    for group, members in g.groups_and_allowed_members(user):
      all_eligible.update(set(members)-{user})
    return all_eligible
  if eligibility_spec['eligible']:
    all_eligible.update(set(c.get_connected_users(user, up_to_degree=eligibility_spec['eligible'])))
  if eligibility_spec['eligible_starred']:
    all_eligible.update(set(repo.starred_users(user)))
  if eligibility_spec['eligible_users']:
    all_eligible.update(set(eligibility_spec['eligible_users']))
  for group in eligibility_spec['eligible_groups']:
    all_eligible.update(set(g.allowed_members_from_group_row(group, user))-{user})
  return all_eligible


def all_eligible_users(request, eligibility_spec):
  user = eligibility_spec['user']
  included_users = _all_included_users(eligibility_spec)
  rels = relationships(included_users, user)
  eligible_users = set()
  for user2 in included_users:
    if _is_eligible(request, user2, rels[user2], included=True):
      eligible_users.add(user2)
  return eligible_users


def requests_to_props(requests, user):
  or_groups = [[r for r in requests if r.or_group_id == or_group_id]
                for or_group_id in {r.or_group_id for r in requests}]
  for this_or_group in or_groups:
    sm.my_assert(h.all_equal([r.elig_with_dict for r in this_or_group]), "same eligibility")
    sm.my_assert(h.all_equal([(r.user, r.min_size, r.max_size) for r in this_or_group]), "same proposer, sizes")
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
    user2_id = this_or_group[0].user
    or_group_id = this_or_group[0].or_group_id
    yield port.Proposal(
      prop_id=or_group_id,
      user=user2_id,
      own=user2_id==user.get_id(),
      min_size=r.min_size,
      max_size=r.max_size,
      eligible_all=r.eligible_all,
      eligible=r.eligible,
      eligible_users=r.eligible_users,
      eligible_groups=r.eligible_groups,
      eligible_starred=r.eligible_starred,
      eligible_invites=r.eligible_invites,
      note=r.exchange_format.note,
      times=times
    )


def eps_to_props(exchange_prospects, user):
  user_id = user.get_id()
  for this_ep in exchange_prospects:
    my_requests = [r for r in this_ep if user_id == r.user]
    own = bool(my_requests)
    rep_request = my_requests[0] if own else this_ep[0]
    user2_id = user_id if own else rep_request.user
    times = [port.ProposalTime(
        time_id=rep_request.request_id, ### problem
        start_now=this_ep.start_now,
        start_date = None if this_ep.start_now else this_ep.start_dt,
        expire_date=this_ep.expire_dt,
        duration=this_ep.exchange_format.duration,
        users_accepting=[r.user for r in this_ep if r.user != user2_id],
    )]
    yield port.Proposal(
      prop_id=this_ep.prospect_id,
      user=user2_id,
      own=own,
      min_size=this_ep.min_size,
      max_size=this_ep.max_size,
      eligible_all=rep_request.eligible_all, ### problem
      eligible=rep_request.eligible, ### problem
      eligible_users=rep_request.eligible_users, ### problem
      eligible_groups=rep_request.eligible_groups, ### problem
      eligible_starred=rep_request.eligible_starred, ### problem
      eligible_invites=rep_request.eligible_invites, ### problem
      times=times
    )


def _request_in_eps(request, exchange_prospects):
  for ep in exchange_prospects:
    if request.request_id in ep.request_ids:
      return True
  return False


def get_proposals_upcomings(user):
  user_exchanges = ei.user_exchanges(user)
  proposals = visible_requests_as_port_view_items(user, user_exchanges)
  upcomings = ei.upcoming_match_dicts(user, user_exchanges)
  return proposals, upcomings


def visible_requests_as_port_view_items(user, user_exchanges):
  user_exchange_request_ids = [id for exchange in user_exchanges for id in exchange.request_ids]
  current_rrs = list(repo.current_requests(records=True))
  _prune_request_records(current_rrs, sm.now())
  viable_rrs = [rr for rr in current_rrs if rr.entity.current and rr.record_id not in user_exchange_request_ids]
  exchange_prospects = list(repo.request_records_prospects(viable_rrs))
  return _proposal_view_items(user, viable_rrs, exchange_prospects)


def _proposal_view_items(user, viable_rrs, exchange_prospects):
  user_id = user.get_id()
  user_requests = [rr.entity for rr in viable_rrs if rr.user == user] # just display user_requests simply, whether or not part of exchange_prospects
  others_request_records = [rr for rr in viable_rrs if rr.user != user]
  others_exchange_prospects = [ep for ep in exchange_prospects if user_id not in ep.users]
  visible_exchange_prospects = list(current_visible_prospects(user, others_exchange_prospects, others_request_records))
  return _to_view_items(user, user_requests, visible_exchange_prospects)


def _to_view_items(user, user_requests, visible_exchange_prospects):
  port_proposals = list(eps_to_props(visible_exchange_prospects, user)) + list(requests_to_props(user_requests, user))
  return port.Proposal.create_view_items(port_proposals)


@sm.background_task_with_reporting
def notify_edit_bg(user, requests, related_prev_requests):
  new_all_eligible_users = _get_new_eligible_users(user, requests)
  old_all_eligible_users = _get_old_eligible_users(related_prev_requests)
  _notify_add(new_all_eligible_users - old_all_eligible_users, user, requests.notify_info)
  if requests.notify_info != related_prev_requests.notify_info:
    _notify_edit(new_all_eligible_users & old_all_eligible_users, user, requests.notify_info)
  _notify_cancel(old_all_eligible_users - new_all_eligible_users, user)


def _get_new_eligible_users(user, requests):
  try:
    (requests.user, requests.or_group_id, requests.elig_with_dict)
  except RuntimeError:
    sm.warning("notify_edit requests no common requester, or_group_id, or elig_with_dict")
  sm.my_assert(user.get_id() == requests.user, f"notify_edit: user ({user.get_id()}) should be requester ({requests.user})")
  new_eligibility_spec = repo.eligibility_spec(requests[0])
  new_all_eligible_users = all_eligible_users(requests[0], new_eligibility_spec)
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
    return all_eligible_users(old_r0, old_eligibility_spec)


def _notify_add(users, requester, requests_info):
  for other_user in users:
    n.notify_requests(other_user, requester, requests_info, f"empathy request", " has requested an empathy chat")


def _notify_edit(users, requester, requests_info):
  for other_user in users:
    n.notify_requests(other_user, requester, requests_info, "empathy request", " has changed their request for an empathy chat")


def _notify_cancel(users, requester):
  for other_user in users:
    n.notify_requests_cancel(other_user, requester, "empathy request")
