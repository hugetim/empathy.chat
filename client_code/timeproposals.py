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
DEFAULT_START_MIN = h.now() + datetime.timedelta(seconds=max(p.WAIT_SECONDS, 60*CANCEL_MIN_MINUTES))
DEFAULT_START = h.now() + datetime.timedelta(minutes=DEFAULT_NEXT_MINUTES)
DEFAULT_START_MAX = h.now() + datetime.timedelta(days=31)
DEFAULT_PROPOSAL = {'start_now': 0,
                    'start_date': DEFAULT_START,
                    'duration': DURATION_DEFAULT_MINUTES,
                    'cancel_buffer': CANCEL_DEFAULT_MINUTES,
                    'alt': [],
                    'eligible': 3,
                    'eligible_users': [],
                    'eligible_groups': [],
                   }

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
