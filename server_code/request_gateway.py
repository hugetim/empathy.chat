import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from abc import ABC, ABCMeta, abstractmethod, abstractproperty
from .requests import Request, Eformat


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
    getattr(app_tables, self._table_name)
  
  @abstractmethod
  def _add(self):
    pass

  @abstractmethod
  def _update(self):
    pass
  
  def __init__(self, entity, row_id=None):
    self._entity = entity
    self.record_id = row_id

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
    self._table.add_row(_request_to_fields(self._entity))

  def _update(self):
    self._row.update(_request_to_fields(self._entity))


def _request_to_fields(request):
  eformat = _get_eformat_row(request.eformat)
  out = dict(eformat=eformat)
  out['user'] = app_tables.users.get_by_id(request.user.user_id)
  simple_keys = [
    'or_group_id',
    'start_dt',
    'expire_dt',
    'create_dt',
    'edit_dt',
    'min_size',
    'max_size',
    'eligible',
    'eligible_users',
    'eligible_groups',
    'eligible_starred',
    'current',
  ]
  for key in simple_keys:
    out[key] = getattr(request, key)
  return out


def _get_eformat_row(eformat):
  row = app_tables.eformats.get(duration=self._entity.eformat.duration)
  if not row:
    row = app_tables.eformats.add_row(duration=self._entity.eformat.duration)
  return row
