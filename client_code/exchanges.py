from collections import namedtuple
from .server_misc import warning


# Participant = namedtuple('Participant', ['user_id', 'present', 'complete', 'slider_value', 'late_notified', 'external'])
Format = namedtuple('Format', ['duration'])


class Exchange:
  def __init__(self, exchange_id, room_code, participants, start_dt, exchange_format):
    self.exchange_id = exchange_id
    self.room_code = room_code
    self.participants = participants
    self.start_dt = start_dt
    self.exchange_format = exchange_format
    
  def my(self, my_user_id):
    [participant] = [p for p in self.participants if p['user_id'] == my_user_id]
    return participant
  
  def their(self, my_user_id):
    other_participants = [p for p in self.participants if p['user_id'] != my_user_id]
    if len(other_participants) > 1:
      warning(f"len(temp_values) > 1, but this function assumes dyads only")
    if other_participants:
      return other_participants[0]
  

  
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
