import anvil.server
from .cluegen import Datum
from .portable import User
from .groups import Group
from datetime import datetime, timedelta


@anvil.server.portable_class 
class Eformat(Datum):
  duration: int
  # def __init__(self, duration=None):
  #   self.duration = duration


@anvil.server.portable_class
class Request():
  # id: str
  # or_group_id: str
  # user: User
  # start_dt: datetime
  # eformat: Eformat
  # expire_dt: datetime
  # create_dt: datetime
  # edit_dt: datetime
  # min_size: int = 2
  # max_size: int = 2
  # eligible: int
  # eligible_users: list
  # eligible_groups: list
  # eligible_starred: bool
  def __init__(self, request_id=None, or_group_id=None, user=None, start_dt=None, eformat=None, expire_dt=None,
               create_dt=None, edit_dt=None, min_size=2, max_size=2,
               eligible=None, eligible_users=None, eligible_groups=None, eligible_starred=None,
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
    self.eligible = eligible
    self.eligible_users = eligible_users if eligible_users else []
    self.eligible_groups = eligible_groups if eligible_groups else []
    self.eligible_starred = eligible_starred
    self.current = current

  def __repr__(self):
    return (
      f"Request({self.request_id!r}, {self.or_group_id!r}, {self.user!r}, {self.start_dt!r}, {self.eformat!r}, {self.expire_dt!r}, "
      f"{self.create_dt!r}, {self.edit_dt!r}, {self.min_size!r}, {self.max_size!r}, "
      f"{self.eligible!r}, {self.eligible_users!r}, {self.eligible_groups!r}, {self.eligible_starred!r}, "
      f"{self.current!r})"
    )
  
  def __str__(self):
    return (
      f"Request({self.request_id!s}, {self.or_group_id!s}, {self.user!s}, {self.start_dt!s}, {self.eformat!s}, {self.expire_dt!s}, "
      f"{self.create_dt!s}, {self.edit_dt!s}, {self.min_size!s}, {self.max_size!s}, "
      f"{self.eligible!s}, {self.eligible_users!s}, {self.eligible_groups!s}, {self.eligible_starred!s}, "
      f"{self.current!s})"
    )
  
  @property
  def start_now(self):
    return self.start_dt < self.expire_dt

  @property
  def end_dt(self):
    return self.start_dt + timedelta(minutes=self.eformat.duration)
  
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
        out.append(other.plus_request(self))
    return out


@anvil.server.portable_class 
class ExchangeProspect:
  def __init__(self, requests):
    if not requests or len(requests) < 1 or not isinstance(requests[0], Request):
      raise ValueError("Input 'requests' must contain at least one Request")
    self._requests = tuple(requests)

  def __repr__(self):
    return f"ExchangeProspect({', '.join(repr(r) for r in self._requests)})"

  def __str__(self):
    return f"{{{', '.join(str(r) for r in self._requests)}}}"
  
  def plus_request(self, request):
    if self.is_full:
      raise RuntimeError("Cannot add request because ExchangeProspect is full")
    return ExchangeProspect(self._requests + (request,))
  
  def __len__(self):
    return len(self._requests)

  def __getitem__(self, index):
    return self._requests[index]

  @property
  def min_size(self):
    return max([r.min_size for r in self._requests])

  @property
  def max_size(self):
    return min([r.max_size for r in self._requests])

  @property
  def _rep_request(self):
    return self._requests[0]
  
  @property
  def eformat(self):
    return self._rep_request.eformat

  @property
  def start_dt(self):
    return self._rep_request.start_dt

  @property
  def start_now(self):
    return self._rep_request.start_now

  @property
  def has_enough(self):
    return len(self) >= self.min_size

  @property
  def is_full(self):
    return len(self) >= self.max_size


def have_conflicts(requests):
  # keep in sync with portable.Proposal.has_conflict
  or_groups = list({r.or_group_id for r in requests})
  for i, or_group in enumerate(or_groups):
    remaining_or_groups = or_groups[i+1:]
    non_or_requests = [r for r in requests if r.or_group_id in remaining_or_groups]
    for r in [r for r in requests if r.or_group_id == or_group]:
      if r.has_conflict(non_or_requests):
        return True
  return False


def potential_matches(new_requests, other_user_requests):
  exchange_prospects = []
  other_exchange_prospects = all_exchange_prospects(other_user_requests)
  for new_request in new_requests:
    exchange_prospects.extend(new_request.get_prospects(other_exchange_prospects))
  return [set(ep) for ep in exchange_prospects]


def all_exchange_prospects(requests):
  return _exchange_prospects(requests)
                            
                          
def _exchange_prospects(remaining_requests, prospects_so_far=None):
  if prospects_so_far is None:
    prospects_so_far = []
  if not remaining_requests:
    return prospects_so_far
  this_proposer = remaining_requests[0].user
  this_proposer_requests = [r for r in remaining_requests if r.user == this_proposer]
  other_user_requests = [r for r in remaining_requests if r.user != this_proposer]
  new_prospects = []
  for r in this_proposer_requests:
    new_prospects.extend(r.get_prospects(prospects_so_far) + [ExchangeProspect([r])])
  prospects_so_far.extend(new_prospects)
  return _exchange_prospects(other_user_requests, prospects_so_far)
  
  