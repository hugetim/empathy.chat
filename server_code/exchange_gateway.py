import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .exceptions import RowMissingError
from .exchanges import Exchange
from .requests import ExchangeFormat
from . import server_misc as sm
from .request_gateway import get_exchange_format_row, RequestRecord, get_user_row_by_id, get_request_row_by_id, row_to_exchange_format


# def _current_exchange_i(user, to_join):
#   """Return earliest if multiple current"""
#   import datetime
#   from .server_misc import now
#   this_match, i = None, None
#   now_plus = now() + datetime.timedelta(minutes=p.START_EARLY_MINUTES)
#   current_matches = app_tables.matches.search(tables.order_by('match_commence', ascending=True), users=[user], complete=[0],
#                                               match_commence=q.less_than_or_equal_to(now_plus))
#   for row in current_matches:
#     temp_i = row['users'].index(user)
#     # Note: 0 used for 'complete' field b/c False not allowed in SimpleObjects
#     if (to_join or row['present'][temp_i] == 1) and row['complete'][temp_i] == 0:
#       this_match = row
#       i = temp_i
#       break
#   return this_match, i


# def _get_participant(match_dict, i):
#   keys = ['present', 'complete', 'late_notified', 'external']
#   participant = {k: match_dict[k][i] for k in keys}
#   participant['user_id'] = match_dict['users'][i].get_id()
#   participant['slider_value'] = match_dict['slider_values'][i]
#   return participant
# #   return Participant(user_id=match_row['users'][i].get_id(), 
# #                      **{k: match_row[k][i] for k in keys})


# def get_exchange(user_id, to_join=False):
#   from .server_misc import get_acting_user
#   user = get_acting_user(user_id)
#   return get_user_exchange(user, to_join)

# def get_user_exchange(user, to_join=False):
#   this_match, i = _current_exchange_i(user, to_join)
#   if this_match:
#     match_dict = dict(this_match)
#     num_participants = len(match_dict['users'])
# #       participants = [_get_participant(match_dict, i)]
# #       for j in range(len(match_dict['users'])):
# #         if j != i:
# #           participants.append(_get_participant(match_dict, j))
#     participants = [_get_participant(match_dict, j) for j in range(num_participants)]
#     return Exchange(exchange_id=this_match.get_id(),
#                     room_code=match_dict['proposal_time']['jitsi_code'],
#                     participants=participants,
#                     start_now=match_dict['proposal_time']['start_now'],
#                     start_dt=match_dict['match_commence'],
#                     exchange_format=ExchangeFormat(match_dict['proposal_time']['duration']),
#                     user_id=user.get_id(),
#                     my_i=i,
#                     )
#   else:
#     raise RowMissingError("Current empathy chat not found for this user")

# @tables.in_transaction(relaxed=True)
# def save_exchange(exchange):
#   """Update participant statuses"""
#   save_exchange_wo_transaction(exchange)

# def save_exchange_wo_transaction(exchange):
#   match_row = _match_row(exchange)
#   keys_to_update = list(exchange.participants[0].keys())
#   keys_to_update.remove('user_id')
#   update_dict = {k: [p[k] for p in exchange.participants] for k in keys_to_update}
#   update_dict['slider_values'] = update_dict.pop('slider_value')
#   match_row.update(**update_dict)

# def create_exchange(exchange, proptime):
#   match_row = app_tables.matches.add_row(users=proptime.all_users(),
#                                           proposal_time=proptime._row,
#                                           match_commence=exchange.start_dt,
#                                         )
#   exchange.exchange_id = match_row.get_id()
#   save_exchange_wo_transaction(exchange)
#   return exchange

def add_chat(from_user, message, now, users):
  to_users = set(users) - set([from_user])
  if len(to_users) > 1:
    raise NotImplementedError("text chat for more than 2 participants not yet supported")
  to_user = to_users.pop()
  app_tables.messages.add_row(from_user=from_user,
                              to_user=to_user,
                              message=message,
                              time_stamp=now)
    
# def get_chat_messages(exchange):
#   match_row = _match_row(exchange)
#   return app_tables.chat.search(tables.order_by("time_stamp", ascending=True), match=match_row)

# def _match_row(self, exchange):
#   return app_tables.matches.get_by_id(exchange.exchange_id)

basic_participants_fields = ['entered_dt', 'complete_dt', 'appearances', 'late_notified', 'slider_value', 'video_external']
participants_fetch = q.fetch_only(*basic_participants_fields, user=q.fetch_only('first_name'), request=q.fetch_only('current'))
basic_exchange_fields = ['room_code', 'start_dt', 'current', 'start_now', 'exchange_format']
exchanges_fetch = q.fetch_only(*basic_exchange_fields,
                               users=q.fetch_only('first_name'),
                               participants=participants_fetch,
                              )


def exchanges_by_user(user, records=False):
  for exchange_row in app_tables.exchanges.search(exchanges_fetch, users=[user], current=True):
    yield ExchangeRecord.from_row(exchange_row) if records else _row_to_exchange(exchange_row)


def exchanges_by_user_starting_prior_to(user, cutoff_dt, records=False):
  rows = app_tables.exchanges.search(exchanges_fetch, users=[user], start_dt=q.less_than(cutoff_dt), current=True)
  for exchange_row in rows:
    yield ExchangeRecord.from_row(exchange_row) if records else _row_to_exchange(exchange_row)


def exchanges_starting_prior_to(cutoff_dt, records=False):
  for exchange_row in app_tables.exchanges.search(exchanges_fetch, start_dt=q.less_than(cutoff_dt), current=True):
    yield ExchangeRecord.from_row(exchange_row) if records else _row_to_exchange(exchange_row)


def exchange_record_with_any_request_records(request_records):
  request_rows = [rr._row for rr in request_records]
  participant_rows_with = app_tables.participants.search(participants_fetch, request=q.any_of(*request_rows))
  if len(participant_rows_with) > 0:
    return ExchangeRecord.from_row(app_tables.exchanges.get(participants=list(participant_rows_with)))
  else:
    return None


class ExchangeRecord(sm.SimpleRecord):
  _table_name = 'exchanges'
  _participant_rows = []

  @staticmethod
  def _row_to_entity(row):
    return _row_to_exchange(row)
  
  @staticmethod
  def _entity_to_fields(entity):
    return _exchange_to_fields(entity)

  def _update_participants(self):
    self._participant_rows = []
    for p in self.entity.participants:
      p_record = ParticipantRecord(p, record_id=p.get('participant_id'))
      p_record.save()
      self._participant_rows.append(p_record._row)
  
  # @property
  # def _my_participant_record(self):
  #   raise NotImplementedError("ExchangeRecord._my_participant_record")

  def _add(self):
    self.__row = self._table.add_row(participants=self._participant_rows, **self._entity_to_fields(self.entity))
    self._row_id = self.__row.get_id()
  
  def _update(self):
    self._row.update(participants=self._participant_rows, **self._entity_to_fields(self.entity))
  
  def save(self):
    self._update_participants()
    if self._row_id is None:
      self._add()
    else:
      self._update()

  @property
  def users(self):
    if self._row_id:
      return self._row['users']
    else:
      return [sm.get_other_user(p['user_id']) for p in self.entity.participants]

  @tables.in_transaction
  def end_in_transaction(self):
    self.end()
  
  def end(self):
    currently_matched_users = [sm.get_other_user(u_id) for u_id in self.entity.currently_matched_user_ids]
    with tables.batch_update:
      for u in currently_matched_users:
        u['status'] = None
      if self._row_id:
        self._row['current'] = False
    self.entity.current = False

  def commence(self):
    for participant in self.entity.participants:
      rr = RequestRecord.from_id(participant['request_id'])
      rr.entity.current = False
      rr.save()
      participant['entered_dt'] = sm.now()
    self.save()
    users = self.users
    with tables.batch_update:
      for user in users:
        user['status'] = "matched"


def _row_to_exchange(row):
  exchange_format = row_to_exchange_format(row['exchange_format'])
  kwargs = dict(exchange_format=exchange_format)
  kwargs['exchange_id'] = row.get_id()
  kwargs['participants'] = [_row_to_participant(participant_row)
                            for participant_row in row['participants']]
  simple_keys = [
    'room_code',
    'start_dt',
    'start_now',
    'current',
  ]
  for key in simple_keys:
    kwargs[key] = row[key]
  return Exchange(**kwargs)

  
def _exchange_to_fields(exchange):
  # participants handled separately
  exchange_format = get_exchange_format_row(exchange.exchange_format)
  out = dict(exchange_format=exchange_format)
  out['users'] = [get_user_row_by_id(p['user_id']) for p in exchange.participants]
  simple_keys = [
    'room_code',
    'start_dt',
    'start_now',
    'current',
  ]
  for key in simple_keys:
    out[key] = getattr(exchange, key)
  return out


class ParticipantRecord(sm.SimpleRecord):
  _table_name = 'participants'

  @staticmethod
  def _row_to_entity(row):
    return _row_to_participant(row)
  
  @staticmethod
  def _entity_to_fields(entity):
    return _participant_to_fields(entity)

  def _update_appearances(self):
    appearance_rows = []
    for a in self.entity.get('appearances', []):
      a_record = AppearanceRecord(a, record_id=a.get('appearance_id'))
      a_record.save()
      appearance_rows.append(a_record._row)
    self._row['appearances'] = appearance_rows

  def save(self):
    if self._row_id is None:
      self._add()
    else:
      self._update()
    self._update_appearances()


def _row_to_participant(participant_row):
  participant = dict(participant_row)
  participant['participant_id'] = participant_row.get_id()
  participant['user_id'] = participant.pop('user').get_id()
  participant['request_id'] = participant.pop('request').get_id()
  participant['appearances'] = [_row_to_appearance(a)
                                for a in participant.pop('appearances')]
  return participant


def _participant_to_fields(participant):
  fields = participant.copy()
  fields.pop('appearances', []) # appearances handled separately
  fields.pop('participant_id', None)
  fields['user'] = get_user_row_by_id(fields.pop('user_id'))
  fields['request'] = get_request_row_by_id(fields.pop('request_id'))
  sm.my_assert(fields['request'] is not None, "Can't save exchange/participant for an unsaved request.")
  return fields
  

class AppearanceRecord(sm.SimpleRecord):
  _table_name = 'appearances'

  @staticmethod
  def _row_to_entity(row):
    return _row_to_appearance(row)
  
  @staticmethod
  def _entity_to_fields(entity):
    return _appearance_to_fields(entity)


def _row_to_appearance(appearance_row):
  return dict(appearance_id=appearance_row.get_id(), **dict(appearance_row))


def _appearance_to_fields(appearance):
  fields = appearance.copy()
  fields.pop('appearance_id', None)
  return fields
  