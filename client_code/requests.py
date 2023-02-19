import anvil.server
from .cluegen import Datum
from .portable import User
from .groups import Group
from . import helper as h
from . import parameters as p
from datetime import datetime, timedelta
import uuid


@anvil.server.portable_class 
class Eformat(Datum):
  duration: int


@anvil.server.portable_class
class Request:
  def __init__(
    self, request_id=None, or_group_id=None,
    user=None,
    start_dt=None, eformat=None, expire_dt=None,
    create_dt=None, edit_dt=None,
    min_size=2, max_size=2, with_users=None,
    eligible=None, eligible_users=None, eligible_groups=None, eligible_starred=None,
    pref_order=None,
    current=None,
  ):
    self.request_id = request_id
    self.or_group_id = or_group_id
    self.user = user
    self.start_dt = start_dt
    self.eformat = eformat
    self.expire_dt = expire_dt
    self.create_dt = create_dt
    self.edit_dt = edit_dt
    self.min_size = min_size
    self.max_size = max_size
    self.with_users = list(with_users) if with_users else []
    self.eligible = eligible
    self.eligible_users = eligible_users if eligible_users else []
    self.eligible_groups = eligible_groups if eligible_groups else []
    self.eligible_starred = eligible_starred
    self.pref_order = pref_order
    self.current = current

  @property
  def elig_with_dict(self):
    return {key: getattr(self, key) for key in ['with_users', 'eligible', 'eligible_users', 'eligible_groups', 'eligible_starred']}
  
  def __repr__(self):
    return (
      f"Request({self.request_id!r}, {self.or_group_id!r}, {self.user!r}, {self.start_dt!r}, {self.eformat!r}, {self.expire_dt!r}, "
      f"{self.create_dt!r}, {self.edit_dt!r}, {self.min_size!r}, {self.max_size!r}, "
      f"{self.eligible!r}, {self.eligible_users!r}, {self.eligible_groups!r}, {self.eligible_starred!r}, "
      f"{self.pref_order!r}), {self.current!r})"
    )
  
  def __str__(self):
    return (
      f"Request({self.request_id!s}, {self.or_group_id!s}, {self.user!s}, {self.start_dt!s}, {self.eformat!s}, {self.expire_dt!s}, "
      f"{self.create_dt!s}, {self.edit_dt!s}, {self.min_size!s}, {self.max_size!s}, "
      f"{self.eligible!s}, {self.eligible_users!s}, {self.eligible_groups!s}, {self.eligible_starred!s}, "
      f"{self.pref_order!s}), {self.current!s})"
    )
  
  @property
  def start_now(self):
    return self.start_dt < self.expire_dt
  
  @property
  def end_dt(self):
    return self.start_dt + timedelta(minutes=self.eformat.duration)

  def expired(self, now):
    return self.expire_dt < now
  
  def has_conflict(self, non_or_requests):
    # keep in sync with requests.have_no_conflicts
    for other in non_or_requests:
      if self.start_dt < other.end_dt and other.start_dt < self.end_dt:
        return True
    return False

  def get_prospects(self, other_exchange_prospects):
    out = []
    for other in other_exchange_prospects:
      if (self.eformat == other.eformat
          and self.min_size <= other.max_size
          and self.max_size >= other.min_size
          and not other.is_full
          and (self.start_dt == other.start_dt or (self.start_now and other.start_now))
         ):
        _possible_ep = other.plus_request(self)
        if _possible_ep.is_possible_to_satisfy_all_with_users:
          out.append(_possible_ep)
    return out

  def has_room_for(self, other_user):
    return 1 + len(self.with_users) + (0 if other_user in self.with_users else 1) <= self.max_size


@anvil.server.portable_class 
class ExchangeProspect:
  def __init__(self, requests):
    if not requests or len(requests) < 1 or not isinstance(next(iter(requests)), Request):
      raise ValueError("Input 'requests' must contain at least one Request")
    self.requests = tuple(requests)

  def __eq__(self, other):
    return isinstance(other, ExchangeProspect) and set(self.requests) == set(other.requests)
  
  def __repr__(self):
    return f"ExchangeProspect({', '.join(repr(r) for r in self.requests)})"

  def __str__(self):
    return f"{{{', '.join(str(r) for r in self.requests)}}}"
  
  def plus_request(self, request):
    if self.is_full:
      raise RuntimeError("Cannot add request because ExchangeProspect is full")
    return ExchangeProspect(self.requests + (request,))
  
  def __len__(self):
    return len(self.requests)

  def __getitem__(self, index):
    return self.requests[index]

  @property
  def is_possible_to_satisfy_all_with_users(self):
    users_set = set(self.users)
    with_users_missing = {u for r in self for u in (set(r.with_users) - users_set)}
    return len(self) + len(with_users_missing) <= self.max_size
    
  @property
  def is_with_users_satisfied(self):
    users = self.users
    for r in self:
      if not set(r.with_users).issubset(users):
        return False
    return True
  
  @property
  def min_size(self):
    return max([r.min_size for r in self.requests])

  @property
  def max_size(self):
    return min([r.max_size for r in self.requests])

  @property
  def has_enough(self):
    return len(self) >= self.min_size and self.is_with_users_satisfied

  @property
  def is_full(self):
    return len(self) >= self.max_size

  @property
  def users(self):
    return tuple((r.user for r in self))
  
  @property
  def _rep_request(self):
    return self.requests[0]
  
  @property
  def eformat(self):
    return self._rep_request.eformat

  @property
  def start_dt(self):
    return self._rep_request.start_dt

  @property
  def end_dt(self):
    return self.start_dt + timedelta(minutes=self.eformat.duration)
  
  @property
  def start_now(self):
    return self._rep_request.start_now

  @property
  def create_dt(self):
    return min([r.create_dt for r in self.requests])    


def have_conflicts(requests):
  # keep in sync with portable.Proposal.has_conflict
  or_groups = [[r for r in requests if r.or_group_id == or_group_id]
               for or_group_id in {r.or_group_id for r in requests}]
  for i, this_or_group in enumerate(or_groups):
    remaining_non_or_requests = [r for or_group in or_groups[i+1:] for r in or_group]
    for r in this_or_group:
      if r.has_conflict(remaining_non_or_requests):
        return True
  return False


def potential_matches(new_requests, other_user_requests):
  other_exchange_prospects = all_exchange_prospects(other_user_requests)
  exchange_prospects = []
  for new_request in new_requests:
    exchange_prospects.extend(new_request.get_prospects(other_exchange_prospects))
  return exchange_prospects #[set(ep) for ep in exchange_prospects]


def all_exchange_prospects(requests):
  return _gather_exchange_prospects(requests)
                            
                          
def _gather_exchange_prospects(remaining_requests, prospects_so_far=None):
  if prospects_so_far is None: prospects_so_far = []
  if not remaining_requests:
    return prospects_so_far
  this_proposer = remaining_requests[0].user
  this_proposer_requests = [r for r in remaining_requests if r.user == this_proposer]
  new_prospects = _combine_requests_w_prospects(this_proposer_requests, prospects_so_far)
  other_user_requests = [r for r in remaining_requests if r.user != this_proposer]
  return _gather_exchange_prospects(other_user_requests, prospects_so_far + new_prospects)


def _combine_requests_w_prospects(this_proposer_requests, prospects_so_far):
  new_prospects = []
  for r in this_proposer_requests:
    new_prospects.extend(r.get_prospects(prospects_so_far) + [ExchangeProspect([r])])
  return new_prospects


def exchange_to_save(new_requests, other_user_requests):
  """If a 'has_enough' exchange exists, return one"""
  exchange_prospects = potential_matches(new_requests, other_user_requests)
  has_enough_exchanges = [ep for ep in exchange_prospects if ep.has_enough]
  if has_enough_exchanges:
    return _selected_exchange(has_enough_exchanges)
  else:
    return None


def _selected_exchange(has_enough_exchanges):
  min_start_dt = min((ep.start_dt for ep in has_enough_exchanges))
  earliest_eps = [ep for ep in has_enough_exchanges if ep.start_dt == min_start_dt]
  if len(earliest_eps) == 1:
    return earliest_eps[0]
  max_size = max((len(ep) for ep in earliest_eps))
  largest_eps = [ep for ep in earliest_eps if len(ep) == max_size]
  if len(largest_eps) == 1:
    return largest_eps[0]
  return min(largest_eps, key=lambda x: x.create_dt)


def prop_to_requests(port_prop, with_users=None, create_dt=None, edit_dt=None, current=True):
  now = h.now()
  or_group_id = port_prop.prop_id if port_prop.prop_id else str(uuid.uuid4())
  for i, port_time in enumerate(port_prop.times):
    start_dt = port_time.start_date
    expire_dt = port_time.expire_date
    if port_time.start_now:
      start_dt = now
      expire_dt = now + timedelta(seconds=p.WAIT_SECONDS)
    yield Request(or_group_id=or_group_id,                  
                  user=port_prop.user.user_id,
                  start_dt=start_dt,
                  expire_dt=expire_dt,
                  eformat=Eformat(port_time.duration),
                  create_dt=create_dt if create_dt else now,
                  edit_dt=create_dt if create_dt else now,
                  min_size=port_prop.min_size,
                  max_size=port_prop.max_size,
                  with_users=with_users if with_users else [],
                  eligible=port_prop.eligible,
                  eligible_users=[port_user.user_id for port_user in port_prop.eligible_users],
                  eligible_groups=port_prop.eligible_groups,
                  eligible_starred=port_prop.eligible_starred,
                  pref_order=i,
                  current=current,
                 )
