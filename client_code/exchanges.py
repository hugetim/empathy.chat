from collections import namedtuple
from .server_misc import warning


# Participant = namedtuple('Participant', ['user_id', 'present', 'complete', 'slider_value', 'late_notified', 'external'])
Format = namedtuple('Format', ['duration'])


class Exchange:
  def __init__(self, exchange_id, room_code, participants, start_now, start_dt, exchange_format, user_id, my_i=None):
    self.exchange_id = exchange_id
    self.room_code = room_code
    self.participants = participants
    self.start_now = start_now
    self.start_dt = start_dt
    self.exchange_format = exchange_format
    if my_i:
      self._my_i = my_i
      self._their_i = self.participants.index(self._their())
    else:
      [participant] = [p for p in self.participants if p['user_id'] == user_id]
      self._my_i = self.participants.index(participant)
      self._their_i = self.participants.index(self._their())

  @property
  def my(self):
    return self.participants[self._my_i]

  @property
  def their(self):
    return self.participants[self._their_i]
  
  def _their(self):
    other_participants = [p for p in self.participants]
    del other_participants[self._my_i]
    if len(other_participants) > 1:
      warning(f"len(temp_values) > 1, but this function assumes dyads only")
    if other_participants:
      return other_participants[0]

  def late_notify_needed(self, now):
    if self.their['present'] or self.their['late_notified']:
      return False
    past_start_time = self.start_dt < now
    return (not self.start_now) and past_start_time

  
# class Participant:
#   def __init__(self, user_id, present, complete, slider_value, late_notified, external):
#     self.user_id = user_id
#     self.present = present
#     self.complete = complete
#     self.slider_value = slider_value
#     self.late_notified = late_notified
#     self.external = external

#   def __repr__(self):
#     return f"Participant({user_id}, {present}, {complete}, {slider_value}, {late_notified}, {external})"
