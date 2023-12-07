import anvil.users
import anvil.server
import datetime
import anvil.tz
from . import helper as h
from . import parameters as p
from . import relationship as rel


DEFAULT_NEXT_MINUTES = 60
DEFAULT_NEXT_DELTA = datetime.timedelta(minutes=DEFAULT_NEXT_MINUTES)
DURATION_DEFAULT_MINUTES = 25
DURATION_TEXT = {15: "5 & 5 (~15 min. total)",
                 25: "10 & 10 (~25 min. total)",
                 35: "15 & 15 (~35 min. total)",
                 45: "20 & 20 (~45 min. total)",
                 55: "25 & 25 (~55 min. total)",
                 65: "30 & 30 (~65 min. total)"}
CANCEL_MIN_MINUTES = 5
CANCEL_DEFAULT_MINUTES = 15
CANCEL_TEXT = {0: "Don't cancel. I'll be there anyway.",
               5: "5 min. prior",
               15: "15 min. prior",
               30: "30 min. prior",
               60: "1 hr. prior",
               120: "2 hrs. prior",
               8*60: "8 hrs. prior",
               24*60: "24 hrs. prior",
               48*60: "48 hrs. prior",
               "custom": "a specific time...",
              }
MAX_ALT_TIMES = 9
UNLINKED = rel.UNLINKED


def last_name(last, relationship=None):
  if not relationship:
    return ""
  if relationship.last_name_visible:
    return last
  elif relationship.last_initial_visible and last:
    return last[0:1] + "."
  else:
    return ""


def full_name(first, last, distance=UNLINKED, relationship=None):
  if relationship is None:
    relationship = rel.Relationship(distance=distance)
  maybe_last = last_name(last, relationship)
  return first + " " + maybe_last if maybe_last else first
    

@anvil.server.portable_class
class User(h.AttributeToKey):
  def __init__(self, user_id=None, name=None, url_confirmed=None, distance=UNLINKED, seeking=None, starred=None):
    self.user_id = user_id
    self.name = name
    self.url_confirmed = url_confirmed
    self.distance = distance
    self.seeking = seeking
    self.starred = starred
    self.relationship = rel.Relationship(distance=self.distance)

  def __str__(self):
    return self.name
  
  def __repr__(self):
    return str(self.__dict__)
  
  def __eq__(self, other):
    return isinstance(other, User) and self.user_id == other.user_id

  def __hash__(self):
    return hash((self.user_id,))
  
  @property
  def distance_str(self):
    return h.add_num_suffix(self.distance) if (self.distance is not None and self.distance < UNLINKED) else ""
 
  def toggle_starred(self):
    from . import glob
    self.starred = not self.starred
    glob.reset_get_create_user_items()

  @staticmethod
  def from_name_item(item):
    return item['value']
  
  @staticmethod
  def from_logged_in():
    from . import glob
    if glob.logged_in_user_id and glob.lazy_loaded:
      return glob.users[glob.logged_in_user_id]
    else:
      logged_in_user = anvil.users.get_user()
      distance = 0
      return User(user_id=logged_in_user.get_id(), 
                  name=full_name(logged_in_user['first_name'], logged_in_user['last_name'], distance=distance),
                  url_confirmed=bool(logged_in_user['url_confirmed_date']),
                  distance=0,
                  seeking=logged_in_user['seeking_buddy'],
                  starred=None,
                )

  
@anvil.server.portable_class
class UserFull(User):
  def __init__(self, user_id=None, name=None, url_confirmed=None, distance=UNLINKED, seeking=None, starred=None,
               degree=UNLINKED, last_active=None, status=None, unread_message=None, me=None, 
               first="", last="", url_confirmed_date=None, trust_level=None, trust_label="",
               common_group_names=None):
    super().__init__(user_id=user_id, name=name, url_confirmed=url_confirmed, distance=distance, seeking=seeking, starred=starred)
    self.degree = degree
    self.last_active = last_active
    self.status = status
    self.unread_message = unread_message
    self.me = me
    self.first = first
    self.last = last
    self.url_confirmed_date = url_confirmed_date
    self.trust_level = trust_level
    self.trust_label = trust_label
    self.common_group_names = common_group_names if common_group_names else []
    self.relationship = rel.Relationship(distance=self.distance, degree=self.degree)

  def name_item(self):
    return dict(key=self.name, value=self, subtext=self.distance_str_or_groups, title=self.first if self.first else self.name)

  @property
  def distance_str(self):
    out = super().distance_str
    if self.status == "invite":
      out += " (pending invite)"
    return out
  
  @property
  def distance_str_or_groups(self):
    d_str = self.distance_str
    return d_str if d_str else "\n".join(self.common_group_names)
  
  @property
  def url_confirmed_date_str(self):
    return h.short_date_str(h.as_local_tz(self.url_confirmed_date)) if self.url_confirmed_date else ""
  
  @property
  def last_active_str(self):
    return h.short_date_str(h.as_local_tz(self.last_active))


@anvil.server.portable_class
class UserProfile(UserFull):
  def __init__(self, relationships=None, how_empathy="", profile="", profile_updated=None, profile_url="", **kwargs):
    super().__init__(**kwargs)
    self.relationships = relationships if relationships else []
    self.how_empathy = how_empathy
    self.profile = profile
    self.profile_updated_dt = profile_updated
    self.profile_url = profile_url
    
  @property
  def profile_updated_date_str(self):
    return h.short_date_str(h.as_local_tz(self.profile_updated_dt)) if self.profile_updated_dt else ""

  @property
  def profile_text_tooltip(self):
    return "To edit, click the pencil button to the right." if self.me else ""

    
@anvil.server.portable_class
class ProposalTime():

  def __init__(self, time_id=None, start_now=False, start_date=None, #status=None, 
               duration=None, expire_date=None,
               accept_date=None, users_accepting=None, jitsi_code=None):
    from .glob import default_request
    self.time_id = time_id
    self.start_now = start_now
    self.start_date = (start_date if (start_date or start_now)
                       else h.round_up_datetime(h.now() + datetime.timedelta(minutes=DEFAULT_NEXT_MINUTES)))
    if duration is not None:
      self.duration = duration
    elif default_request is not None:
      self.duration = default_request['prop_time']['duration']
    else:
      self.duration = DURATION_DEFAULT_MINUTES
    if expire_date or start_now:
      self.expire_date = expire_date
    else:
      cancel_buffer = (CANCEL_DEFAULT_MINUTES if not default_request 
                       else default_request['prop_time']['cancel_buffer'])
      self.expire_date = (self.start_date 
                          - datetime.timedelta(minutes=cancel_buffer))
    self.accept_date = accept_date
    self.users_accepting = users_accepting if users_accepting else []
    self.jitsi_code = jitsi_code

  def __serialize__(self, global_data):
    dict_rep = self.__dict__
    dict_rep['start_now'] = int(self.start_now)
    return dict_rep

  def __deserialize__(self, data, global_data):
    self.__dict__.update(data)
    self.start_now = bool(self.start_now)

  def __repr__(self):
    return str(self.__dict__)
 
  @property
  def start_for_order(self):
    return h.now() if self.start_now else self.start_date

  def has_conflict(self, conflict_checks):
    # keep in sync with requests.have_no_conflicts
    if conflict_checks:
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
    >>>(ProposalTime(start_now=False, start_date=h.now()).get_errors()
        == {'start_date': ("Start time must be at least " 
                           + str(CANCEL_MIN_MINUTES) + " minutes away "
                           + '(unless "Cancel if not accepted by" Advanced option set to "{CANCEL_TEXT[0]}")')
    True
    """
    now = h.now()
    messages = {}
    if not self.start_now:
      if self.start_date < now:
        messages['start_date'] = ("Start time must be in the future.")
      elif (self.start_date != self.expire_date 
            and self.start_date < (now + datetime.timedelta(minutes=CANCEL_MIN_MINUTES))):
        messages['start_date'] = ("Start time must be at least " 
                                  + str(CANCEL_MIN_MINUTES) + " minutes away "
                                  + f'(unless "Cancel if not accepted by" Advanced option set to "{CANCEL_TEXT[0]}")')
      else:
        if self.expire_date < now:
          cancel_buffer = round((self.start_date-self.expire_date).total_seconds()/60)
          if cancel_buffer in CANCEL_TEXT.keys():
            messages['start_date'] = ("Start time must be at least " 
                                      + h.seconds_to_words(cancel_buffer*60) + ' away (due to the "Cancel if not accepted by" Advanced setting below).')
          else:
            messages['cancel_buffer'] = 'The specified "Cancel" time has already passed.'
        elif self.expire_date > self.start_date:
          messages['cancel_buffer'] = ('The "Cancel" time must be prior to all start times (by at least '
                                      + str(CANCEL_MIN_MINUTES) + ' minutes).')
        elif (self.start_date != self.expire_date
              and self.expire_date > (self.start_date
                                      - datetime.timedelta(minutes=CANCEL_MIN_MINUTES))):
          messages['cancel_buffer'] = ('The "Cancel" time must be at least ' 
                                      + str(CANCEL_MIN_MINUTES) + ' minutes prior to all start times.')
    if self.has_conflict(conflict_checks):
      messages['start_date'] = ("Time/duration overlaps with one of your existing requests.")
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
    return {'s_min': now + datetime.timedelta(seconds=p.WAIT_SECONDS),
            'start': now + datetime.timedelta(minutes=DEFAULT_NEXT_MINUTES),
            's_max': now + datetime.timedelta(days=31)}
        
      
@anvil.server.portable_class 
class Proposal():
  def __init__(self, prop_id=None, own=True, user=None, times=None, min_size=2, max_size=2,
               eligible_all=None, eligible=None, eligible_users=None, eligible_groups=None, eligible_starred=None,
               eligible_invites=None, note=""):
    from .glob import default_request
    self.prop_id = prop_id
    self.own = own
    self.user = user # should rename proposer
    if times is not None:
      self.times = times 
    elif default_request:
      self.times = [ProposalTime(start_now=default_request['prop_time']['start_now'])]
    else:
      self.times = [ProposalTime()]
    self.min_size = min_size
    self.max_size = max_size
    if eligible_all is not None:
      self.eligible_all = eligible_all
    else:
      self.eligible_all = default_request['eligible'].get('eligible_all') if default_request else True
    if eligible is not None:
      self.eligible = eligible
    else:
      self.eligible = default_request['eligible'].get('eligible', 0) if default_request else 0
    if eligible_users is not None:
      self.eligible_users = eligible_users
    else:
      from . import glob
      self.eligible_users = [glob.users[id] for id in default_request['eligible']['eligible_users'] if id in glob.users] if default_request else []
    if eligible_groups is not None:
      self.eligible_groups = eligible_groups
    else:
      from . import network_controller as nc
      self.eligible_groups = [nc.get_group_by_id(id) for id in default_request['eligible']['eligible_groups']] if default_request else [] #i01
    if eligible_starred is not None:
      self.eligible_starred = eligible_starred
    else:
      self.eligible_starred = default_request['eligible']['eligible_starred'] if default_request else True
    self.eligible_invites = eligible_invites if eligible_invites else []
    self.note = note

  @property
  def start_now(self):
    return self.times[0].start_now
  
  def __serialize__(self, global_data):
    dict_rep = self.__dict__
    dict_rep['own'] = int(self.own)
    return dict_rep

  def __deserialize__(self, data, global_data):
    self.__dict__.update(data)
    self.own = bool(self.own)

  def __repr__(self):
    return str(self.__dict__)  

  @property
  def eligibility_desc(self):
    items = []
    if self.eligible_all:
      return "My whole network"
    if self.eligible_invites:
      items.append(", ".join([str(i) for i in self.eligible_invites]))
    if self.eligible_starred:
      items.append('Starred')
    if self.eligible_users:
      items.append(", ".join([str(u) for u in self.eligible_users]))
    if self.eligible:
      desc = {1: "1st degree connections", 2: "connections up to 2 degrees", 3: "connections up to 3 degrees"}
      items.append(desc[self.eligible])
    if self.eligible_groups:
      items.append(", ".join([str(g) for g in self.eligible_groups]))
    return "; ".join(items) if items else "(no one)"
  
  # @property
  # def specific_user_eligible(self):
  #   if (self.eligible == 0 and len(self.eligible_users) == 1 
  #       and not self.eligible_groups and not self.eligible_starred):
  #     return self.eligible_users[0]
  #   else:
  #     return None
   
  def get_check_items(self):
    items = []
    if self.own:
      for time in self.times:
        items.append(time.get_check_item())
    return items

  def get_default_request_update(self):
    from .groups import Group
    item = self.create_form_item()
    out = dict(prop_time={k: item[k] for k in ['start_now', 'duration']})
    if not item['start_now']:
      t0 = self.times[0]
      out['prop_time']['cancel_buffer'] = round((t0.start_date - t0.expire_date).total_seconds()/60)      
    out['eligible'] = {k: item.get(k) for k in ['eligible_all', 'eligible', 'eligible_starred']}
    out['eligible']['eligible_users'] = [port_user.user_id for port_user in item['eligible_users']]
    out['eligible']['eligible_groups'] = [group.group_id for group in item['eligible_groups']]
    return out
  
  def create_form_item(self, status=None, conflict_checks=None):
    """Convert a proposal dictionary to the format of self.item"""
    item = {'prop_id': self.prop_id,
            'min_size': self.min_size,
            'max_size': self.max_size,
            'eligible_all': self.eligible_all,
            'eligible': self.eligible, 
            'eligible_users': self.eligible_users, 
            'eligible_groups': self.eligible_groups,
            'conflict_checks': conflict_checks,
            'eligible_starred': self.eligible_starred,
            'eligible_invites': self.eligible_invites,
            'note': self.note,
           }
    first, *alts = self.times
    item['now_allowed'] = not(status and first.start_now == False)
    item.update(first.create_form_item())
    item['alt'] = [time.create_form_item() for time in alts]
    if not h.all_equal([item['cancel_buffer']] + [alt_item['cancel_buffer'] for alt_item in item['alt']]):
      if not item['cancel_date'] or item['cancel_buffer'] != "custom":
        item['cancel_date'] = item['start_date'] - datetime.timedelta(minutes=item['cancel_buffer'])
        item['cancel_buffer'] = "custom"
      for alt_item in item['alt']:
        if not alt_item['cancel_date'] or alt_item['cancel_buffer'] != "custom":
          alt_item['cancel_date'] = alt_item['start_date'] - datetime.timedelta(minutes=alt_item['cancel_buffer'])
          alt_item['cancel_buffer'] = "custom"
        h.my_assert(alt_item['cancel_date'] == item['cancel_date'], "all custom cancel_dates same")
                                                                              
    return item

  @staticmethod
  def from_create_form(item):
    first_time = ProposalTime.from_create_form(item)
    alts = [ProposalTime.from_create_form(alt) for alt in item['alt']]
    return Proposal(prop_id=item.get('prop_id'),
                    times=[first_time] + alts,
                    min_size = item['min_size'],
                    max_size = item['max_size'],
                    eligible_all=item['eligible_all'],
                    eligible=item['eligible'],
                    eligible_users=item['eligible_users'],
                    eligible_groups=item['eligible_groups'],
                    eligible_starred=item['eligible_starred'],
                    eligible_invites=item['eligible_invites'],
                    note=item['note'],
                   )

  @staticmethod
  def create_view_items(port_proposals):
    items = []
    own_count = 0
    total_own_count = sum([prop.own for prop in port_proposals])
    for prop in port_proposals:
      own_count += prop.own
      for i, time in enumerate(prop.times):
        items.append({'prop_time': time, 'prop': prop,
                      'prop_num': own_count, 'prop_count': total_own_count, 'times_i': i})
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
