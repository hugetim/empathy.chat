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
  
  def __init__(self, entity, row_id=None, row=None):
    self._entity = entity
    self._row_id = row_id
    self._row = row

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

  def expired(self, now):
    return self._entity.expired(now)

  def cancel(self, now):
    self._row['current'] = False
    self._entity.current = False

  @property
  def current(self):
    return self._entity.current
  
  @property
  def user(self):
    if self._row:
      return self._row['user']
    else:
      return sm.get_other_user(self._entity.user)

  @property
  def eligibility_spec(self):
    spec = {}
    spec['user'] = self.user
    spec['eligible'] = self._entity.eligible
    spec['eligible_starred'] = self._entity.eligible_starred
    if self._row:
      spec['eligible_users'] = self._row['eligible_users']
      spec['eligible_groups'] = self._row['eligible_groups']
    else:
      spec['eligible_users'] = [sm.get_other_user(user_id) for user_id in self._entity.eligible_users]
      spec['eligible_groups'] = [app_tables.groups.get_by_id(port_group.group_id)
                                for port_group in self._entity.eligible_groups]
    return spec
  
  @staticmethod
  def from_row(row):
    request = _row_to_request(row)
    return RequestRecord(request, row.get_id(), row)


def _request_to_fields(request):
  eformat = _get_eformat_row(request.eformat)
  out = dict(eformat=eformat)
  out['user'] = app_tables.users.get_by_id(request.user)
  out['with_users'] = [sm.get_other_user(user_id)
                       for user_id in request.with_users]
  out['eligible_users'] = [sm.get_other_user(user_id)
                           for user_id in request.eligible_users]
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


def _row_to_request(row):
  eformat = Eformat(duration=row['eformat']['duration'])
  kwargs = dict(eformat=eformat)
  kwargs['request_id'] = row.get_id()
  kwargs['user'] = row['user'].get_id()
  kwargs['with_users'] = [user2.get_id()
                          for user2 in row['with_users']]
  kwargs['eligible_users'] = [user2.get_id()
                              for user2 in row['eligible_users']]
  kwargs['eligible_groups'] = [groups.Group(group_row['name'], group_row.get_id())
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
    yield _row_to_request(request_row)


def current_requests(records=False):
  for request_row in app_tables.requests.search(current=True):
    yield RequestRecord.from_row(request_row) if records else _row_to_request(request_row)


def partially_matching_requests(partial_request_dicts, now, records=False):
  q_expressions = [
    q.all_of(eformat=_get_eformat_row(prd['eformat']),
             **(dict(start_dt=q.less_than(now)) if prd['start_now'] else dict(start_dt=prd['start_dt']))
            )
    for prd in partial_request_dicts
  ]
  rows = app_tables.requests.search(q.any_of(*q_expressions), current=True)
  for request_row in rows:
    yield RequestRecord.from_row(request_row) if records else _row_to_request(request_row)
    

# def get_potential_matching_requests(requests):
#   """Return requests with same start time and eformat as any of `requests`"""
#   out = {}
#   eformats = {r.eformat for r in requests}
#   for ef in eformats:
#     ef_row = _get_eformat_row(ef)
#     start_dts = 
#     out.extend(app_tables.requests.search(eformat=ef_row))
