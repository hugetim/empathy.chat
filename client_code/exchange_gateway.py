import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .exceptions import RowMissingError


class ExchangeRepository:
  def __init__(self, user):
    from . import matcher
    this_match, i = matcher.current_match_i(user)
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

  def update_my_external(self, my_external):
    temp_values = self._exchange['external']
    temp_values[self._user_i] = int(my_external)
    self._exchange['external'] = temp_values
    
  def mark_present(self):
    if not self._exchange['present'][self._user_i]:
      temp = self._exchange['present']
      temp[self._user_i] = 1
      self._exchange['present'] = temp
      
  def exchange_i(self):
    return dict(self._exchange), self._user_i
  
  def chat_messages(self):
    return app_tables.chat.search(tables.order_by("time_stamp", ascending=True), match=self._exchange)