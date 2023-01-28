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

  @property
  def start_now(self, now=None):
    if now is None:
      now = datetime.now()
    return self.start_dt < now and self.expire_dt > now

  @property
  def end_dt(self):
    return self.start_dt + timedelta(minutes=self.eformat.duration)
  
  def has_conflict(self, non_or_requests):
    # keep in sync with requests.have_no_conflicts
    for other in non_or_requests:
      if self.start_dt < other.end_dt and other.start_dt < self.end_dt:
        return True
    return False


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
