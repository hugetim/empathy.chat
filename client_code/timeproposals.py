import anvil.server
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


@anvil.server.portable_class
class ProposalTime():

  def __init__(self, time_id=None, start_now=True, start_date=None, 
               duration=DURATION_DEFAULT_MINUTES, expire_date=None):
    self.time_id = time_id      
    self.start_now = start_now 
    self.start_date = (start_date if (start_date or start_now)
                       else h.now() + datetime.timedelta(minutes=DEFAULT_NEXT_MINUTES))
    self.duration = duration
    if expire_date:
      self.expire_date = expire_date
    else:
      if start_now:
        self.expire_date = h.now() + datetime.timedelta(seconds=p.WAIT_SECONDS)
      else:
        self.expire_date = (self.start_date 
                            - datetime.timedelta(minutes=CANCEL_DEFAULT_MINUTES))
      
  def __serialize__(self, global_data):
    dict_rep = self.__dict__
    dict_rep['start_now'] = int(self.start_now)
    return dict_rep

  def __deserialize__(self, data, global_data):
    self.__dict__.update(data)
    self.start_now = bool(self.start_now)

  def time_prop_item(self):
    time_dict = {key: self.__dict__[key] for key in ['time_id', 'start_now', 'start_date', 'duration']}
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
  def default_start():
    now=h.now()
    return {'s_min': now + datetime.timedelta(seconds=max(p.WAIT_SECONDS, 60*CANCEL_MIN_MINUTES)),
            'start': now + datetime.timedelta(minutes=DEFAULT_NEXT_MINUTES),
            's_max': now + datetime.timedelta(days=31)}
        
      
@anvil.server.portable_class 
class Proposal():
  
  def __init__(self, prop_id=None, own=True, name=None, times=[ProposalTime()], 
               eligible=3, eligible_users=[], eligible_groups=[]):
    self.prop_id = prop_id
    self.own = own
    self.name = name
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
          
  def create_form_item(self):
    """Convert a proposal dictionary to the format of self.item"""
    item = {key: self.__dict__[key] for key in ['prop_id', 'eligible', 'eligible_users', 'eligible_groups']}
    first, *alts = self.times
    item.update(first.time_prop_item())
    item['alt'] = [time.time_prop_item() for time in alts]
    return item

    
#DEFAULT_PROPOSAL = {'start_now': 0,
#                    'start_date': DEFAULT_START,
#                    'duration': DURATION_DEFAULT_MINUTES,
#                    'cancel_buffer': CANCEL_DEFAULT_MINUTES,
#                    'alt': [],
#                    'eligible': 3,
#                    'eligible_users': [],
#                    'eligible_groups': [],
#                   }


def default_cancel_date(now, start_date):
    minutes_prior = max(CANCEL_MIN_MINUTES,
                        min(CANCEL_DEFAULT_MINUTES,
                        ((start_date - now).seconds/60)/2))
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
