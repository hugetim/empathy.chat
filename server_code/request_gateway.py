import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from abc import ABC, ABCMeta, abstractmethod, abstractproperty
from .requests import Request, Eformat
from . import server_misc as sm
from . import groups


# class SimpleRecord(Record, metaclass=ABCMeta): 
#   @abstractmethod
#   def _fields(self):
#     pass
    
#   def _add(self):
#     self._row = self._table.add_row(**self._fields())

#   def _update(self):
#     self._row.update(**self._fields())


class Record(ABC): 
  _row = None
  _row_id = None

  @abstractproperty
  def _table_name(self):
    pass

  @property
  def _table(self):
    return getattr(app_tables, self._table_name)
  
  @abstractmethod
  def _add(self):
    pass

  @abstractmethod
  def _update(self):
    pass
  
  def __init__(self, entity, row_id=None):
    self._entity = entity
    self._row_id = row_id

  def save(self):
    if not self._row_id:
      self._add()
      return
    if not self._row:
      self._row = self._table.get_by_id(self._row_id)
    self._update()

  @property
  def record_id(self):
    return self._row_id


class RequestRecord(Record):
  _table_name = 'requests'

  def _add(self):
    self._row = self._table.add_row(**_request_to_fields(self._entity))
    self._row_id = self._row.get_id()

  def _update(self):
    self._row.update(**_request_to_fields(self._entity))


def _request_to_fields(request):
  eformat = _get_eformat_row(request.eformat)
  out = dict(eformat=eformat)
  out['user'] = app_tables.users.get_by_id(request.user.user_id)
  out['eligible_users'] = [sm.get_other_user(port_user.user_id)
                           for port_user in request.eligible_users]
  out['eligible_groups'] = [app_tables.groups.get_by_id(port_group.group_id)
                            for port_group in request.eligible_groups]
  simple_keys = [
    'or_group_id',
    'start_dt',
    'expire_dt',
    'create_dt',
    'edit_dt',
    'min_size',
    'max_size',
    'eligible',
    'eligible_starred',
    'current',
  ]
  for key in simple_keys:
    out[key] = getattr(request, key)
  return out


def _row_to_request(row, user):
  eformat = Eformat(duration=row['eformat']['duration'])
  kwargs = dict(eformat=eformat)
  kwargs['request_id'] = row.get_id()
  kwargs['user'] = sm.get_port_user(row['user'], user1=user, simple=True)
  kwargs['eligible_users'] = [sm.get_port_user(user2, user1=user, simple=True)
                              for user2 in row['eligible_users']]
  out['eligible_groups'] = [groups.Group(group_row['name'], group_row.get_id())
                            for group_row in row['eligible_groups']]
  simple_keys = [
    'or_group_id',
    'start_dt',
    'expire_dt',
    'create_dt',
    'edit_dt',
    'min_size',
    'max_size',
    'eligible',
    'eligible_starred',
    'current',
  ]
  for key in simple_keys:
    kwargs[key] = row[key]
  return Request(**kwargs)


def _get_eformat_row(eformat):
  row = app_tables.eformats.get(duration=eformat.duration)
  if not row:
    row = app_tables.eformats.add_row(duration=eformat.duration)
  return row


def requests_by_user(user):
  request_rows = app_tables.requests.search(user=user, current=True)
  for request_row in request_rows:
    yield _row_to_request(request_row, user)


def current_requests():
  for request_row in app_tables.requests.search(current=True):
    yield _row_to_request(request_row, user)
    
    
# def get_potential_matching_requests(requests):
#   """Return requests with same start time and eformat as any of `requests`"""
#   out = {}
#   eformats = {r.eformat for r in requests}
#   for ef in eformats:
#     ef_row = _get_eformat_row(ef)
#     start_dts = 
#     out.extend(app_tables.requests.search(eformat=ef_row))
