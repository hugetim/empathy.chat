import anvil.server
from .cluegen import Datum
from .portable import User
from .groups import Group
from datetime import datetime


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
