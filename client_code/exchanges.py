from collections import namedtuple


Participant = namedtuple('Participant', ['user_id', 'present', 'complete', 'slider_value', 'late_notified', 'external'])
Format = namedtuple('Format', ['duration'])


class Exchange:
  def __init__(self, room_code, participants, start_dt, exchange_format):
    self.room_code = room_code
    self.participants = participants
    self.start_dt = start_dt
    self.exchange_format = exchange_format
    
  def my_slider_value(self):
    return None

  
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
