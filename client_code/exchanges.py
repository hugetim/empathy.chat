from collections import namedtuple
from . import helper as h
from . import parameters as p
from .requests import Request, ExchangeProspect, ExchangeFormat


# Participant = namedtuple('Participant', ['user_id', 'present', 'complete', 'slider_value', 'late_notified', 'external'])
# Format = namedtuple('Format', ['duration'])


class Exchange:
  def __init__(self, exchange_id, room_code, participants, # list of dicts
               start_now, start_dt, exchange_format, user_id=None, my_i=None, current=None):
    self.exchange_id = exchange_id
    self.room_code = room_code
    self.participants = participants
    self.start_now = start_now
    self.start_dt = start_dt
    self.exchange_format = exchange_format
    self.set_my(user_id, my_i)
    self.current = current

  def set_my(self, user_id=None, my_i=None):
    if my_i:
      self._my_i = my_i
      self._their_i = self.participants.index(self._their())
    elif user_id:
      [participant] = [p for p in self.participants if p['user_id'] == user_id]
      self._my_i = self.participants.index(participant)
      self._their_i = self.participants.index(self._their())
  
  @staticmethod
  def from_exchange_prospect(ep: ExchangeProspect, now=None):
    start_now = ep.start_now
    now = now if now is not None else h.now()
    if (start_now and (now - ep.start_dt).total_seconds() <= p.BUFFER_SECONDS):
      entered_dt = now
    else:
      entered_dt = None
    return Exchange(
      exchange_id=None,
      room_code=h.new_jitsi_code(),
      participants=[
        dict(participant_id=None,
             user_id=r.user,
             request_id=r.request_id,
             entered_dt=entered_dt,
             appearances=[],
             late_notified=None,
             slider_value=None,
             video_external=None,
             complete_dt=None) 
        for r in ep.requests
      ],
      start_now=start_now,
      start_dt=ep.start_dt if not start_now else now,
      exchange_format=ep.exchange_format,
      current=True,
    )

  @property
  def size(self):
    return len(self.participants)

  @property
  def any_appeared(self):
    return bool([p for p in self.participants if p['appearances']])

  @property
  def request_ids(self):
    return [p['request_id'] for p in self.participants]
  
  @property
  def user_ids(self):
    return [p['user_id'] for p in self.participants]

  def start_appearance(self, time_dt):
    self.my['appearances'].append(dict(start_dt=time_dt, end_dt=time_dt, appearance_id=None))

  def continue_appearance(self, time_dt):
    if self.my['appearances']:
      appearance = self.my['appearances'][-1]
      appearance['end_dt'] = time_dt
    else:
      self.start_appearance(time_dt)
  
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
      h.warning(f"len(temp_values) > 1, but this function assumes dyads only")
    if other_participants:
      return other_participants[0]

  def participant_by_id(self, user_id):
    return next((p for p in self.participants if p['user_id'] == user_id))

  @property
  def currently_matched_user_ids(self):
    if self.current:
      return [p['user_id'] for p in self.participants if p['entered_dt'] and not p['complete_dt']]
    else:
      return []
  
  def late_notify_needed(self, now):
    if self.their['appearances'] or self.their['late_notified']:
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
