import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .requests import Request, ExchangeFormat
from . import server_misc as sm
from . import groups
from . import invite_gateway as ig


def _row_to_request(row):
  exchange_format = ExchangeFormat(duration=row['exchange_format']['duration'])
  kwargs = dict(exchange_format=exchange_format)
  kwargs['request_id'] = row.get_id()
  kwargs['user'] = row['user'].get_id()
  kwargs['with_users'] = [user2.get_id()
                          for user2 in row['with_users']]
  kwargs['eligible_users'] = [user2.get_id()
                              for user2 in row['eligible_users']]
  kwargs['eligible_groups'] = [groups.Group(group_row['name'], group_row.get_id())
                               for group_row in row['eligible_groups']]
  kwargs['eligible_invites'] = [ig.get_invite_from_link_key(row['link_key']).portable()
                               for row in row['eligible_invites']]  
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
    'pref_order',
    'current',
  ]
  for key in simple_keys:
    kwargs[key] = row[key]
  return Request(**kwargs)


def _request_to_fields(request):
  exchange_format = get_exchange_format_row(request.exchange_format)
  out = dict(exchange_format=exchange_format)
  out['user'] = sm.get_other_user(request.user)
  out['with_users'] = [sm.get_other_user(user_id)
                       for user_id in request.with_users]
  out['eligible_users'] = [sm.get_other_user(user_id)
                           for user_id in request.eligible_users]
  out['eligible_groups'] = [app_tables.groups.get_by_id(port_group.group_id)
                            for port_group in request.eligible_groups]
  out['eligible_invites'] = [app_tables.invites.get_by_id(port_invite.invite_id)
                             for port_invite in request.eligible_invites]
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
    'pref_order',
    'current',
  ]
  for key in simple_keys:
    out[key] = getattr(request, key)
  return out


class RequestRecord(sm.SimpleRecord):
  _table_name = 'requests'

  @staticmethod
  def _row_to_entity(row):
    return _row_to_request(row)

  @staticmethod
  def _entity_to_fields(entity):
    return _request_to_fields(entity)

  def cancel(self):
    if self._row_id:
      self._row['current'] = False
    self.entity.current = False
    if self.entity.start_now:
      self.user['status'] = None

  def update_expire_dt(self, expire_dt):
    self._row['expire_dt'] = expire_dt
  
  @property
  def user(self):
    if self._row_id:
      return self._row['user']
    else:
      return sm.get_other_user(self.entity.user)

  @property
  def eligibility_spec(self):
    spec = {}
    spec['user'] = self.user
    spec['eligible'] = self.entity.eligible
    spec['eligible_starred'] = self.entity.eligible_starred
    if self._row_id:
      spec['eligible_users'] = self._row['eligible_users']
      spec['eligible_groups'] = self._row['eligible_groups']
    else:
      spec['eligible_users'] = [sm.get_other_user(user_id) for user_id in self.entity.eligible_users]
      spec['eligible_groups'] = [app_tables.groups.get_by_id(port_group.group_id)
                                 for port_group in self.entity.eligible_groups]
    return spec


def eligibility_spec(request):
  spec = {}
  spec['user'] = sm.get_other_user(request.user)
  spec['eligible'] = request.eligible
  spec['eligible_starred'] = request.eligible_starred
  spec['eligible_users'] = [sm.get_other_user(user_id) for user_id in request.eligible_users]
  spec['eligible_groups'] = [app_tables.groups.get_by_id(port_group.group_id)
                             for port_group in request.eligible_groups]
  return spec


def get_exchange_format_row(exchange_format):
  row = app_tables.exchange_formats.get(duration=exchange_format.duration)
  if not row:
    row = app_tables.exchange_formats.add_row(duration=exchange_format.duration)
  return row


def requests_by_user(user, records=False):
  request_rows = app_tables.requests.search(user=user, current=True)
  for request_row in request_rows:
    yield RequestRecord.from_row(request_row) if records else _row_to_request(request_row)


def current_requests(records=False):
  for request_row in app_tables.requests.search(current=True):
    yield RequestRecord.from_row(request_row) if records else _row_to_request(request_row)


def requests_by_or_group(or_group_ids, records=False):
  for request_row in app_tables.requests.search(current=True, or_group_id=q.any_of(*or_group_ids)):
    yield RequestRecord.from_row(request_row) if records else _row_to_request(request_row)


def partially_matching_requests(user, partial_request_dicts, now, records=False):
  q_expressions = [
    q.all_of(exchange_format=get_exchange_format_row(prd['exchange_format']),
             **(dict(start_dt=q.less_than(now)) if prd['start_now'] else dict(start_dt=prd['start_dt']))
            )
    for prd in partial_request_dicts
  ]
  rows = app_tables.requests.search(q.any_of(*q_expressions), user=q.not_(user), current=True)
  for request_row in rows:
    yield RequestRecord.from_row(request_row) if records else _row_to_request(request_row)
