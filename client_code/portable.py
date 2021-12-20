import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import datetime
import anvil.tz
from . import helper as h
from . import parameters as p


DEFAULT_NEXT_MINUTES = 60
DEFAULT_NEXT_DELTA = datetime.timedelta(minutes=DEFAULT_NEXT_MINUTES)
DURATION_DEFAULT_MINUTES = 25
DURATION_TEXT = {15: "15 min. (5 & 5)",
                 25: "25 min. (10 & 10)",
                 35: "35 min. (15 & 15)",
                 45: "45 min. (20 & 20)",
                 55: "55 min. (25 & 25)",
                 65: "65 min. (30 & 30)"}
CANCEL_MIN_MINUTES = 5
CANCEL_DEFAULT_MINUTES = 15
CANCEL_TEXT = {5: "5 min. prior",
               15: "15 min. prior",
               30: "30 min. prior",
               60: "1 hr. prior",
               120: "2 hrs. prior",
               8*60: "8 hrs. prior",
               24*60: "24 hrs. prior",
               48*60: "48 hrs. prior",
               "custom": "a specific time...",
              }


def last_name(last, distance=3):
  return last if distance <= 2 else ""


def full_name(first, last, distance=3):
  maybe_last = last_name(last, distance)
  return first + (" " + maybe_last if maybe_last else "")
    

@anvil.server.portable_class
class User():
  
  def __init__(self, user_id=None, name=None, confirmed_url=None, distance=None, seeking=None, starred=None):
    self.user_id = user_id
    self.name = name
    self.confirmed_url = confirmed_url
    self.distance = distance
    self.seeking = seeking
    self.starred = starred

  def name_item(self):
    return (self.name, self.user_id)

  def __str__(self):
    return self.name
  
  def __repr__(self):
    return str(self.__dict__)
  
  @property
  def s_user(self):
    return app_tables.users.get_by_id(self.user_id)
  
  @staticmethod
  def from_name_item(item):
    return User(item(1), item(0))
  
  @staticmethod
  def from_logged_in():
    logged_in_user = anvil.users.get_user()
    distance = 0
    return User(user_id=logged_in_user.get_id(), 
                name=full_name(logged_in_user['first_name'], logged_in_user['last_name'], distance=distance),
                confirmed_url=bool(logged_in_user['confirmed_url']),
                distance=0,
                seeking=logged_in_user['seeking_buddy'],
                starred=None,
               )

    
@anvil.server.portable_class
class ProposalTime():

  def __init__(self, time_id=None, start_now=False, start_date=None, #status=None, 
               duration=DURATION_DEFAULT_MINUTES, expire_date=None,
               accept_date=None, users_accepting=None, jitsi_code=None):
    self.time_id = time_id
    self.start_now = start_now 
    self.start_date = (start_date if (start_date or start_now)
                       else h.round_up_datetime(h.now() + datetime.timedelta(minutes=DEFAULT_NEXT_MINUTES)))
    self.duration = duration
    if expire_date or start_now:
      self.expire_date = expire_date
    else:
      self.expire_date = (self.start_date 
                          - datetime.timedelta(minutes=CANCEL_DEFAULT_MINUTES))
    self.accept_date = accept_date
    self.users_accepting = users_accepting
    self.jitsi_code = jitsi_code
      
  def __serialize__(self, global_data):
    dict_rep = self.__dict__
    dict_rep['start_now'] = int(self.start_now)
    return dict_rep

  def __deserialize__(self, data, global_data):
    self.__dict__.update(data)
    self.start_now = bool(self.start_now)

  def has_conflict(self, conflict_checks):
    this = self.get_check_item()
    for check_item in conflict_checks:
      if this['start'] < check_item['end'] and check_item['start'] < this['end']:
        return True
    return False
    
  def get_check_item(self):
    start = h.now() if self.start_now else self.start_date
    return {'start': start,
            'end': start + datetime.timedelta(minutes=self.duration)}

  def get_errors(self, conflict_checks=None):
    """Return a dictionary of errors
    >>>(ProposalTime(start_now=False, start_date= h.now()).get_errors()
        == {'start_date': ("The Start Time must be at least " 
                          + str(CANCEL_MIN_MINUTES) + " minutes away.")}
    True
    """
    now = h.now()
    messages = {}
    if not self.start_now:
      if self.start_date < (now + datetime.timedelta(minutes=CANCEL_MIN_MINUTES)):
        messages['start_date'] = ("The Start Time must be at least " 
                                  + str(CANCEL_MIN_MINUTES) + " minutes away.")
      else:
        if self.expire_date < now:
          messages['cancel_buffer'] = 'The specified "Cancel" time has already passed.'
        elif self.expire_date > self.start_date:
          messages['cancel_buffer'] = ('The "Cancel" time must be prior to the Start Time (by at least '
                                      + str(CANCEL_MIN_MINUTES) + ' minutes).')
        elif self.expire_date > (self.start_date 
                                 - datetime.timedelta(minutes=CANCEL_MIN_MINUTES)):
          messages['cancel_buffer'] = ('The "Cancel" time must be at least ' 
                                      + str(CANCEL_MIN_MINUTES) + ' minutes prior to the Start Time.')
    return messages
  
  def create_form_item(self):
    time_dict = {'time_id': self.time_id, 
                 'start_now': self.start_now, 
                 'start_date': self.start_date, 
                 'duration': self.duration,
                 'save_ready': True,}
    if self.start_now:
      time_dict['cancel_buffer'] = CANCEL_DEFAULT_MINUTES
      time_dict['cancel_date'] = None
    else:
      cancel_buffer = round((self.start_date-self.expire_date).total_seconds()/60)
      if cancel_buffer in CANCEL_TEXT.keys():
        time_dict['cancel_buffer'] = cancel_buffer
        time_dict['cancel_date'] = None
      else:
        time_dict['cancel_buffer'] = "custom"
        time_dict['cancel_date'] = self.expire_date
    return time_dict

  @staticmethod
  def from_create_form(item):
    start_now = item.get('start_now', False)
    if start_now:
      expire_date = None
    else:
      expire_date = (item['cancel_date'] if item['cancel_buffer'] == "custom"
                     else (item['start_date'] 
                           - datetime.timedelta(minutes=item['cancel_buffer'])))
    return ProposalTime(time_id=item.get('time_id'),
                        start_now=start_now,
                        start_date=item['start_date'],
                        duration=item['duration'],
                        expire_date=expire_date,
                        accept_date=item.get('accept_date'), 
                        users_accepting=item.get('users_accepting'), 
                        jitsi_code=item.get('jitsi_code'),
                       )
 
  @staticmethod  
  def default_start():
    now=h.now()
    return {'s_min': now + datetime.timedelta(seconds=max(p.WAIT_SECONDS, 60*CANCEL_MIN_MINUTES)),
            'start': now + datetime.timedelta(minutes=DEFAULT_NEXT_MINUTES),
            's_max': now + datetime.timedelta(days=31)}
        
      
@anvil.server.portable_class 
class Proposal():

  MAX_ALT_TIMES = 4
  
  def __init__(self, prop_id=None, own=True, user=None, times=[ProposalTime()], 
               eligible=2, eligible_users=[], eligible_groups=[]):
    self.prop_id = prop_id
    self.own = own
    self.user = user
    self.times = times
    self.eligible = eligible
    self.eligible_users = eligible_users
    self.eligible_groups = eligible_groups
        
  def __serialize__(self, global_data):
    dict_rep = self.__dict__
    dict_rep['own'] = int(self.own)
    return dict_rep

  def __deserialize__(self, data, global_data):
    self.__dict__.update(data)
    self.own = bool(self.own)

  def get_check_items(self):
    items = []
    if self.own:
      for time in self.times:
        items.append(time.get_check_item())
    return items
  
  def create_form_item(self, status=None, conflict_checks=None):
    """Convert a proposal dictionary to the format of self.item"""
    item = {'prop_id': self.prop_id, 
            'eligible': self.eligible, 
            'eligible_users': [port_user.user_id for port_user in self.eligible_users], 
            'eligible_groups': self.eligible_groups,
            'conflict_checks': conflict_checks,}
    first, *alts = self.times
    item['now_allowed'] = not(status and first.start_now == False)
    item.update(first.create_form_item())
    item['alt'] = [time.create_form_item() for time in alts]
    return item

  @staticmethod
  def from_create_form(item):
    first_time = ProposalTime.from_create_form(item)
    alts = [ProposalTime.from_create_form(alt) for alt in item['alt']]
    non_dash_items = [user_item for user_item in item['user_items']
                      if user_item != "---"]
    name_dict = {user_id: name for name, user_id in non_dash_items}
    eligible_users = [User(user_id=user_id, name=name_dict[user_id])
                      for user_id in item['eligible_users']]
    return Proposal(prop_id=item.get('prop_id'),
                    times=[first_time] + alts,
                    eligible=item['eligible'],
                    eligible_users=eligible_users,
                    eligible_groups=item['eligible_groups'],
                   )

  @staticmethod
  def create_view_items(port_proposals):
    items = []
    own_count = 0
    for prop in port_proposals:
      own_count += prop.own
      for time in prop.times:
        items.append({'prop_time': time, 'prop': prop,
                      'prop_num': own_count})
    return items
  
  @staticmethod
  def props_from_view_items(items):
    props = set()
    for item in items:
      props.add(item['prop'])
    for prop in props:
      yield prop
  
#DEFAULT_PROPOSAL = {'start_now': 0,
#                    'start_date': DEFAULT_START,
#                    'duration': DURATION_DEFAULT_MINUTES,
#                    'cancel_buffer': CANCEL_DEFAULT_MINUTES,
#                    'alt': [],
#                    'eligible': 2,
#                    'eligible_users': [],
#                    'eligible_groups': [],
#                   }


def default_cancel_date(now, start_date):
  minutes_prior = max(CANCEL_MIN_MINUTES,
                      min(CANCEL_DEFAULT_MINUTES,
                      ((start_date - now).total_seconds()/60)/2))
  return start_date - datetime.timedelta(minutes=minutes_prior)

  
def closest_duration(dur):
  """Return the closest DURATION_TEXT key to dur
  >>>closest_duration(24)
  25
  """
  durations = DURATION_TEXT.keys()
  return min(durations, key = lambda duration: abs(duration-dur))


def get_proposal_times_errors(now, proposal):
  """Return a dictionary of errors in a time proposal dictionary
  >>>(get_proposal_times_errors(h.now(), {'start_now': 0, start_date': h.now()})
      == {'start_date': ("The Start Time must be at least " 
                         + str(CANCEL_MIN_MINUTES) + " minutes away.")}
  True
  """
  messages = {}
  if not proposal['start_now']:
    if proposal['start_date'] < (now 
                                 + datetime.timedelta(minutes=CANCEL_MIN_MINUTES)):
      messages['start_date'] = ("The Start Time must be at least " 
                                + str(CANCEL_MIN_MINUTES) + " minutes away.")
    else:
      cancel_date = (proposal['start_date'] 
                     - datetime.timedelta(minutes=proposal['cancel_buffer']))
      if cancel_date < now:
        messages['cancel_buffer'] = 'The specified "Cancel" time has already passed.'
      elif cancel_date > proposal['start_date']:
        messages['cancel_buffer'] = ('The "Cancel" time must be prior to the Start Time (by at least '
                                     + str(CANCEL_MIN_MINUTES) + ' minutes).')
      elif cancel_date > (proposal['start_date'] 
                          - datetime.timedelta(minutes=CANCEL_MIN_MINUTES)):
        messages['cancel_buffer'] = ('The "Cancel" time must be at least ' 
                                     + str(CANCEL_MIN_MINUTES) + ' minutes prior to the Start Time.')
  return messages
