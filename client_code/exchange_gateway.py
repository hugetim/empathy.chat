import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from . import parameters as p
from .exceptions import RowMissingError
from .data_helper import DataTableFlatSO


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
    # Note: 0 used for 'complete' field b/c False not allowed in SimpleObjects
    if row['complete'][i] == 0:
      this_match = row
      i = row['users'].index(user)
      break
  return this_match, i


class ExchangeRepository:
  def __init__(self, user):
    this_match, i = _current_exchange_i(user)
    if this_match:
      self._user = user
      self._user_i = i
      self._exchange = this_match
    else:
      raise(RowMissingError("Current empathy chat not found for this user"))
      
  def add_chat(self, message, now):
    app_tables.chat.add_row(match=self._exchange,
                            user=self._user,
                            message=message,
                            time_stamp=now,
                           )

  def submit_slider(self, value):
    DataTableFlatSO(self._exchange, 'slider_values')[self._user_i] = value
    return self.exchange_i()
    
  def update_my_external(self, my_external):
    DataTableFlatSO(self._exchange, 'external')[self._user_i] = my_external

  def complete(self):
    # Note: 0/1 used for 'complete' b/c Booleans not allowed in SimpleObjects
    DataTableFlatSO(self._exchange, 'complete')[self._user_i] = 1
    
  def mark_present(self):
    if not self._exchange['present'][self._user_i]:
      DataTableFlatSO(self._exchange, 'present')[self._user_i] = 1
      
  def exchange_i(self):
    return self.exchange, self._user_i
  
  @property
  def exchange(self):
    return dict(self._exchange)
  
  def chat_messages(self):
    return app_tables.chat.search(tables.order_by("time_stamp", ascending=True), match=self._exchange)
