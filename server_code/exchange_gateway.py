import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from . import parameters as p
from .exceptions import RowMissingError
from .exchanges import Exchange
from .requests import ExchangeFormat
from . import server_misc as sm
from .request_gateway import get_exchange_format_row, RequestRecord


def _current_exchange_i(user, to_join):
  """Return earliest if multiple current"""
  import datetime
  from .server_misc import now
  this_match, i = None, None
  now_plus = now() + datetime.timedelta(minutes=p.START_EARLY_MINUTES)
  current_matches = app_tables.matches.search(tables.order_by('match_commence', ascending=True), users=[user], complete=[0],
                                              match_commence=q.less_than_or_equal_to(now_plus))
  for row in current_matches:
    temp_i = row['users'].index(user)
    # Note: 0 used for 'complete' field b/c False not allowed in SimpleObjects
    if (to_join or row['present'][temp_i] == 1) and row['complete'][temp_i] == 0:
      this_match = row
      i = temp_i
      break
  return this_match, i


def _get_participant(match_dict, i):
  keys = ['present', 'complete', 'late_notified', 'external']
  participant = {k: match_dict[k][i] for k in keys}
  participant['user_id'] = match_dict['users'][i].get_id()
  participant['slider_value'] = match_dict['slider_values'][i]
  return participant
#   return Participant(user_id=match_row['users'][i].get_id(), 
#                      **{k: match_row[k][i] for k in keys})


class ExchangeRepository:
  def get_exchange(self, user_id, to_join=False):
    from .server_misc import get_acting_user
    user = get_acting_user(user_id)
    return self.get_user_exchange(user, to_join)

  def get_user_exchange(self, user, to_join=False):
    this_match, i = _current_exchange_i(user, to_join)
    if this_match:
      match_dict = dict(this_match)
      num_participants = len(match_dict['users'])
#       participants = [_get_participant(match_dict, i)]
#       for j in range(len(match_dict['users'])):
#         if j != i:
#           participants.append(_get_participant(match_dict, j))
      participants = [_get_participant(match_dict, j) for j in range(num_participants)]
      return Exchange(exchange_id=this_match.get_id(),
                      room_code=match_dict['proposal_time']['jitsi_code'],
                      participants=participants,
                      start_now=match_dict['proposal_time']['start_now'],
                      start_dt=match_dict['match_commence'],
                      exchange_format=ExchangeFormat(match_dict['proposal_time']['duration']),
                      user_id=user.get_id(),
                      my_i=i,
                     )
    else:
      raise RowMissingError("Current empathy chat not found for this user")

  @tables.in_transaction(relaxed=True)
  def save_exchange(self, exchange):
    """Update participant statuses"""
    self.save_exchange_wo_transaction(exchange)

  def save_exchange_wo_transaction(self, exchange):
    match_row = self._match_row(exchange)
    keys_to_update = list(exchange.participants[0].keys())
    keys_to_update.remove('user_id')
    update_dict = {k: [p[k] for p in exchange.participants] for k in keys_to_update}
    update_dict['slider_values'] = update_dict.pop('slider_value')
    match_row.update(**update_dict)

  def create_exchange(self, exchange, proptime):
    match_row = app_tables.matches.add_row(users=proptime.all_users(),
                                           proposal_time=proptime._row,
                                           match_commence=exchange.start_dt,
                                          )
    exchange.exchange_id = match_row.get_id()
    self.save_exchange_wo_transaction(exchange)
    return exchange

  def add_chat(self, message, now, exchange):
    match_row = self._match_row(exchange)
    user = app_tables.users.get_by_id(exchange.my['user_id'])
    app_tables.chat.add_row(match=match_row,
                            user=user,
                            message=message,
                            time_stamp=now,
                           )
      
  # def get_chat_messages(self, exchange):
  #   match_row = self._match_row(exchange)
  #   return app_tables.chat.search(tables.order_by("time_stamp", ascending=True), match=match_row)
  
  def _match_row(self, exchange):
    return app_tables.matches.get_by_id(exchange.exchange_id)


def exchanges_by_user(user, records=False):
  for exchange_row in app_tables.exchanges.search(users=[user], current=True):
    yield ExchangeRecord.from_row(exchange_row) if records else _row_to_exchange(exchange_row)


class ExchangeRecord(sm.SimpleRecord):
  _table_name = 'exchanges'

  @staticmethod
  def _row_to_entity(row):
    return _row_to_exchange(row)
  
  @staticmethod
  def _entity_to_fields(entity):
    return _exchange_to_fields(entity)

  def _update_participants(self):
    participant_rows = []
    for p in self.entity.participants:
      p_record = ParticipantRecord(p, record_id=p.get('participant_id'))
      p_record.save()
      participant_rows.append(p_record._row)
    self._row['participants'] = participant_rows
  
  # @property
  # def _my_participant_record(self):
  #   raise NotImplementedError("ExchangeRecord._my_participant_record")
  
  def save(self):
    if self._row_id is None:
      self._add()
    else:
      self._update()
    self._update_participants()


def _row_to_exchange(row):
  exchange_format = ExchangeFormat(duration=row['exchange_format']['duration'])
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
  out['users'] = [app_tables.users.get_by_id(p['user_id']) for p in exchange.participants]
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
  participant['user_id'] = participant.pop('user').get_id()
  participant['request_id'] = participant.pop('request').get_id()
  participant['appearances'] = [_row_to_appearance(a)
                                for a in participant.pop('appearances')]
  return participant


def _participant_to_fields(participant):
  fields = participant.copy()
  fields.pop('appearances', []) # appearances handled separately
  fields.pop('participant_id', None)
  fields['user'] = app_tables.users.get_by_id(fields.pop('user_id'))
  fields['request'] = app_tables.requests.get_by_id(fields.pop('request_id'))
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
  