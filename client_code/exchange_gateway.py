import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from . import parameters as p
from .exceptions import RowMissingError
from .exchanges import Exchange, Format


# def in_transaction(relaxed=False):
#   return tables.in_transaction(relaxed=relaxed)


def _current_exchange_i(user):
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
    if row['complete'][temp_i] == 0:
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
  def get_exchange(self, user_id):
    from .server_misc import get_user
    user = get_user(user_id)
    this_match, i = _current_exchange_i(user)
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
                      exchange_format=Format(match_dict['proposal_time']['duration']),
                      user_id=user.get_id(),
                      my_i=i,
                     )
    else:
      raise(RowMissingError("Current empathy chat not found for this user"))

  @tables.in_transaction(relaxed=True)
  def save_exchange(self, exchange):
    """Update participant statuses"""
    match_row = self._match_row(exchange)
    keys_to_update = list(exchange.participants[0].keys())
    keys_to_update.remove('user_id')
    update_dict = {k: [p[k] for p in exchange.participants] for k in keys_to_update}
    update_dict['slider_values'] = update_dict.pop('slider_value')
    match_row.update(**update_dict)
    
  def add_chat(self, message, now, exchange):
    match_row = self._match_row(exchange)
    user = app_tables.users.get_by_id(exchange.my['user_id'])
    app_tables.chat.add_row(match=match_row,
                            user=user,
                            message=message,
                            time_stamp=now,
                           )
      
  def get_chat_messages(self, exchange):
    match_row = self._match_row(exchange)
    return app_tables.chat.search(tables.order_by("time_stamp", ascending=True), match=match_row)
  
  def _match_row(self, exchange):
    return app_tables.matches.get_by_id(exchange.exchange_id)
