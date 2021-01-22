import anvil.tables
from anvil.tables import app_tables
import anvil.tables.query as q
import anvil.server
import datetime
import anvil.tz
from . import parameters as p
from . import server_misc as sm
from . import portable as port


authenticated_callable = anvil.server.callable(require_user=True)
TEST_TRUST_LEVEL = 10
DEBUG = True


def _seconds_left(status, expire_date=None, ping_start=None):
  now = sm.now()
  if status in ["pinging", "pinged"]:
    if ping_start:
      confirm_match = p.CONFIRM_MATCH_SECONDS - (now - ping_start).seconds
    else:
      confirm_match = p.CONFIRM_MATCH_SECONDS
    if status == "pinging":
      return confirm_match + 2*p.BUFFER_SECONDS # accounts for delay in response arriving
    elif status == "pinged":
      return confirm_match + p.BUFFER_SECONDS # accounts for delay in ping arriving
  elif status == "requesting":
    if expire_date:
      return (expire_date - now).seconds
    else:
      return p.WAIT_SECONDS
  elif status in [None, "matched"]:
    return None
  else:
    print("matcher.seconds_left(s,lc,ps): " + status)

    
def _prune_proposals():
  """Prune definitely outdated prop_times, unmatched then matched, then proposals"""
  if DEBUG:
    print("_prune_proposals")
  now = sm.now()
  proposals_to_check = set()
  if DEBUG:
    print("old_prop_times")
  old_prop_times = app_tables.proposal_times.search(current=True, 
                                                    jitsi_code="",
                                                    expire_date=q.less_than(now),
                                                   )
  for row in old_prop_times:
    ProposalTime(row).cancel_time_only()
    proposals_to_check.add(row['proposal'])
  # below (matched separately) ensures that no ping proposal_times left hanging by cancelling only one
  if DEBUG:
    print("timeout")
  timeout = datetime.timedelta(seconds=p.WAIT_SECONDS + p.CONFIRM_MATCH_SECONDS + 2*p.BUFFER_SECONDS)
  cutoff_r = now - timeout
  if DEBUG:
    print("old_ping_prop_times")
  old_ping_prop_times = app_tables.proposal_times.search(current=True, 
                                                         start_now=True,
                                                         jitsi_code=q.not_(""),
                                                         accept_date=q.less_than(cutoff_r)
                                                        )
  if DEBUG:
    print("old_ping_prop_times2")
  for row in old_ping_prop_times:
    if DEBUG:
      print("old_ping_prop_times3")
    ProposalTime(row).cancel_time_only()
    if DEBUG:
      print("old_ping_prop_times4")
    proposals_to_check.add(row['proposal'])
  # now proposals, after proposal times so they get removed if all times are
  if DEBUG:
    print("old_proposals")
  for row in proposals_to_check:
    if DEBUG:
      print("old_proposals2")
    Proposal(row).cancel_if_no_times()

    
def _prune_matches():
  """Complete old commenced matches for all users"""
  if DEBUG:
    print("_prune_matches")
  assume_complete = datetime.timedelta(hours=4)
  cutoff_m = sm.now() - assume_complete
  if DEBUG:
    print("_prune_matches2")
  # Note: 0 used for 'complete' field b/c False not allowed in SimpleObjects
  old_matches = app_tables.matches.search(complete=[0],
                                          match_commence=q.less_than(cutoff_m),
                                         )
  if DEBUG:
    print("_prune_matches3")
  for row in old_matches:
    if DEBUG:
      print("_prune_matches4")
    temp = row['complete']
    for i in range(len(temp)):
      if DEBUG:
        print("_prune_matches5")
      # Note: 1 used for 'complete' field b/c True not allowed in SimpleObjects
      temp[i] = 1
    if DEBUG:
      print("_prune_matches6")
    row['complete'] = temp


@authenticated_callable
@anvil.tables.in_transaction
def init():
  """
  Runs upon initializing app
  Side effects: prunes old proposals/matches,
                updates expire_date if currently requesting/ping
  """
  print("('init')")
  sm.initialize_session()
  # Prune expired items for all users
  _prune_proposals()
  _prune_matches()
  sm.prune_messages()
  # Initialize user info
  user = anvil.server.session['user']
  print(user['email'])
  trust_level = sm.get_user_info(user)
  email_in_list = None
  name = None
  if trust_level == 0:
    email_in_list = False #sm.email_in_list(user)
    if email_in_list:
      trust_level = 1
      user['trust_level'] = trust_level
      name = user['name']
  elif trust_level < 0:
    email_in_list = False
  else:
    name = user['name']
  test_mode = trust_level >= TEST_TRUST_LEVEL
  # Initialize user status
  state = _get_status(user)
  if state['status'] == 'pinged' and state['seconds_left'] <= 0:
    state = _cancel(user)
  elif state['status'] == 'pinged':
    state = _match_commenced(user)
  elif state['status'] == 'pinging' and state['seconds_left'] <= 0:
    state = _cancel_other(user)
  if state['status'] in ('requesting', 'pinged', 'pinging'):
    state = confirm_wait_helper(user)
  return {'test_mode': test_mode,
          'status': state['status'],
          'seconds_left': state['seconds_left'],
          'proposals': state['proposals'],
          'email_in_list': email_in_list,
          'name': name,
         }


@authenticated_callable
@anvil.tables.in_transaction
def confirm_wait(user_id=""):
  """updates expire_date for current request, returns _get_status(user)"""
  print("confirm_wait", user_id)
  user = sm.get_user(user_id)
  return confirm_wait_helper(user)


def confirm_wait_helper(user, proptime=None):
  """updates expire_date for current request, returns _get_status(user)"""
  if DEBUG:
    print("confirm_wait_helper")
  if proptime:
    current_proptime = proptime
  else:
    current_proptime = ProposalTime.get_now_proposing(user)
  if current_proptime:
    current_proptime.confirm_wait()
  if user:
    return _get_status(user)
  else:
    return None


@authenticated_callable
@anvil.tables.in_transaction
def get_status(user_id=""):
  user = sm.get_user(user_id)
  return _get_status(user)


def _get_status(user):
  """Returns current_status, seconds_left, proposals
  ping_start: accept_date or, for "matched", match_commence
  assumes 2-person matches only
  assumes now proposals only
  Side effects: prune proposals when status in ["requesting", None]
  """
  if DEBUG:
    print("_get_status")
  current_proptime = ProposalTime.get_now_proposing(user)
  expire_date = None
  ping_start = None
  proposals = []
  if current_proptime and current_proptime.is_now():
    expire_date = current_proptime.get_expire_date()
    if current_proptime.is_accepted():
      status = "pinged"
      ping_start = current_proptime.get_ping_start()
    else:
      status = "requesting"
      proposals = Proposal.get_port_proposals(user)
  else:
    current_accept_time = ProposalTime.get_now_accepting(user)
    if current_accept_time and current_accept_time.is_accepted():
      status = "pinging"
      ping_start = current_accept_time.get_ping_start()
      expire_date = current_accept_time.get_expire_date()
    else:
      this_match = current_match(user)
      if this_match:
        status = "matched"
        ping_start = this_match['match_commence']
      else:
        status = None
        proposals = Proposal.get_port_proposals(user)
  return {'status': status, 
          'seconds_left': _seconds_left(status, expire_date, ping_start), 
          'proposals': proposals,
         }


def has_status(user):
  """
  returns bool(current_status)
  """
  current_proptime = ProposalTime.get_now(user)
  if current_proptime:
    return True
  else:
    this_match = current_match(user)
    if this_match:
      return True
  return False


@authenticated_callable
@anvil.tables.in_transaction
def get_code(user_id=""):
  """Return jitsi_code, duration (or Nones)"""
  print("get_code", user_id)
  user = sm.get_user(user_id)
  
  current_proptime = ProposalTime.get_now(user)
  if current_proptime:
    return current_proptime.get_code()
  else:
    this_match = current_match(user)
    if this_match:
      proptime = this_match['proposal_time']
      return proptime.get_code()
  return None, None


@authenticated_callable
@anvil.tables.in_transaction
def accept_proposal(proptime_id, user_id=""):
  """Return _get_status
  
  Side effect: update proptime table with acceptance, if available
  """
  print("accept_proposal", proptime_id, user_id)
  user = sm.get_user(user_id)
  return ProposalTime.get_by_id(proptime_id).attempt_accept(user)


@authenticated_callable
@anvil.tables.in_transaction
def add_proposal(proposal, user_id=""):
  """Return _get_status
  
  Side effect: Update proposal tables with additions, if valid
  """
  print("add_proposal", user_id)
  user = sm.get_user(user_id)
  state, prop_id = _add_proposal(user, proposal)
  return state


def _add_proposal(user, port_prop):
  state = _get_status(user)
  status = state['status']
  if status is None or not port_prop.times[0].start_now:
    prop_id = Proposal.add(user, port_prop).get_id()
  else:
    prop_id = None
  return _get_status(user), prop_id


@authenticated_callable
@anvil.tables.in_transaction
def edit_proposal(proposal, user_id=""):
  """Return _get_status
  
  Side effect: Update proposal tables with revision, if valid
  """
  print("edit_proposal", user_id)
  user = sm.get_user(user_id)
  return _edit_proposal(user, proposal)

    
def _edit_proposal(user, port_proposal):
  print("Not yet preventing editing from making multiple now proposals")
  Proposal.get_by_id(port_proposal.prop_id).update(port_proposal)
  return _get_status(user)


def _cancel(user, proptime_id=None):
  if DEBUG:
    print("_cancel", proptime_id)
  if proptime_id:
    proptime = ProposalTime.get_by_id(proptime_id)
  else:
    proptime = ProposalTime.get_now(user)
  if proptime:
    proptime.cancel_this(user)
  return _get_status(user)

  
@authenticated_callable
@anvil.tables.in_transaction
def cancel(proptime_id=None, user_id=""):
  """Remove proptime and cancel pending match (if applicable)
  Return _get_status
  """
  print("cancel", proptime_id, user_id)
  user = sm.get_user(user_id)
  return _cancel(user, proptime_id)


def _cancel_other(user, proptime_id=None):
  if DEBUG:
    print("_cancel_other", proptime_id)
  if proptime_id:
    proptime = ProposalTime.get_by_id(proptime_id)
  else:
    proptime = ProposalTime.get_now(user)
  if proptime:
    proptime.cancel_other(user)
  return _get_status(user)


@authenticated_callable
@anvil.tables.in_transaction
def cancel_other(proptime_id=None, user_id=""):
  """Return new _get_status
  Upon failure of other to confirm match
  cancel match (if applicable)--and cancel their request
  """
  print("cancel_other", proptime_id, user_id)
  user = sm.get_user(user_id)
  return _cancel_other(user, proptime_id)


@authenticated_callable
@anvil.tables.in_transaction
def match_commenced(proptime_id=None, user_id=""):
  """Return _get_status(user)
  Upon first commence, copy row over and delete "matching" row.
  Should not cause error if already commenced
  """
  print("match_commenced", proptime_id, user_id)
  user = sm.get_user(user_id)
  return _match_commenced(user, proptime_id)


def _match_commenced(user, proptime_id=None):
  """Return _get_status(user)
  Upon first commence, copy row over and delete "matching" row.
  Should not cause error if already commenced
  """
  if DEBUG:
    print("_match_commenced")
  if proptime_id:
    print("proptime_id")
    current_proptime = ProposalTime.get_by_id(proptime_id)
  else:
    current_proptime = ProposalTime.get_now(user)
  if current_proptime:
    print("current_proptime")
    if current_proptime.is_accepted():
      print("'accepted'")
      match_start = sm.now()
      users = current_proptime.all_users()
      new_match = app_tables.matches.add_row(users=users,
                                             proposal_time=current_proptime.row(),
                                             match_commence=match_start,
                                             complete=[0]*len(users))
      # Note: 0 used for 'complete' b/c False not allowed in SimpleObjects
      current_proptime.cancel()
  return _get_status(user)


@authenticated_callable
@anvil.tables.in_transaction
def match_complete(user_id=""):
  """Switch 'complete' to true in matches table for user, return status."""
  print("match_complete", user_id)
  user = sm.get_user(user_id)
  # Note: 0/1 used for 'complete' b/c Booleans not allowed in SimpleObjects
  this_match, i = current_match_i(user)
  temp = this_match['complete']
  temp[i] = 1
  this_match['complete'] = temp
  return _get_status(user)


def current_match(user):
  this_match = None
  current_matches = app_tables.matches.search(users=[user], complete=[0])
  for row in current_matches:
    i = row['users'].index(user)
    # Note: 0 used for 'complete' field b/c False not allowed in SimpleObjects
    if row['complete'][i] == 0:
      this_match = row
  return this_match


def current_match_i(user):
  this_match = None
  current_matches = app_tables.matches.search(users=[user], complete=[0])
  for row in current_matches:
    i = row['users'].index(user)
    # Note: 0 used for 'complete' field b/c False not allowed in SimpleObjects
    if row['complete'][i] == 0:
      this_match = row
  return this_match, i


class ProposalTime():
  
  def __init__(self, proptime_row):
    self.proptime_row = proptime_row

  def get_id(self):
    return self.proptime_row.get_id()  
    
  def portable(self):
    row_dict = dict(self.proptime_row)
    row_dict['time_id'] = self.get_id()
    users_accepting = row_dict.pop('users_accepting')
    if users_accepting:
      row_dict['users_accepting'] = [port.User.get(user) for user in users_accepting]
    else:
      row_dict['users_accepting'] = []
#     if row_dict.pop('current'):
#       row_dict['status'] = "current"
#     elif row_dict.pop('cancelled'):
#       row_dict['status'] = "cancelled"
#     else:
#       row_dict['status'] = "hidden"
    assert row_dict['current'] and not row_dict['cancelled']
    del row_dict['current']
    del row_dict['cancelled']
    del row_dict['missed_pings']
    del row_dict['proposal']
    return port.ProposalTime(**row_dict)

  def row(self):
    return self.proptime_row

  def is_now(self):
    return self.proptime_row['start_now']

  def get_expire_date(self):
    return self.proptime_row['expire_date']

  def get_ping_start(self):
    return self.proptime_row['accept_date']
  
  def get_code(self):
    return self.proptime_row['jitsi_code'], self.proptime_row['duration']
  
  def proposal(self):
    return Proposal(self.proptime_row['proposal'])

  def is_accepted(self):
    return bool(self.proptime_row['jitsi_code'])

  def all_users(self):
    return [self.proposal().proposer()] + list(self.proptime_row['users_accepting'])
  
  def attempt_accept(self, user):
    if DEBUG:
      print("_attempt_accept_proptime")
    state = _get_status(user)
    status = state['status']
    if status in [None, "requesting"]:
      if (self.proptime_row['current'] and (not self.proptime_row['users_accepting'])
          and self.proposal().is_visible(user)):
        self._accept(user, status)
    return _get_status(user)
   
  def _accept(self, user, status):
    if DEBUG:
      print("_accept_proptime")
    now = sm.now()
    if status == "requesting":
      own_now_proposal_time = ProposalTime.get_now_proposing(user)
      if own_now_proposal_time:
        ProposalTime(own_now_proposal_time).cancel()
    self.proptime_row['users_accepting'] = [user]
    self.proptime_row['accept_date'] = now
    self.proptime_row['jitsi_code'] = sm.new_jitsi_code()
    if (self.proptime_row['expire_date'] 
        - datetime.timedelta(seconds=_seconds_left("requesting")) 
        - now).seconds <= p.BUFFER_SECONDS:
      _match_commenced(user)
    else:
      self.proposal().pinged_email()

  def in_users_accepting(self, user):
    return self.proptime_row['users_accepting'] and user in self.proptime_row['users_accepting']
      
  def remove_accepting(self, user=None):
    # below code assumes only dyads allowed
    self.proptime_row['users_accepting'] = []
    self.proptime_row['accept_date'] = None
    self.proptime_row['jitsi_code'] = ""

  def cancel_other(self, user):
    if self.in_users_accepting(user):
      self.cancel(missed_ping=1)
    elif self.proposal().proposer() == user:
      # below code assumes only dyads allowed
      self.remove_accepting()
      if self.is_expired():
        self.cancel()  
    
  def cancel_this(self, user):
    if self.in_users_accepting(user):
      self.remove_accepting()
      if self.is_expired():
       self.cancel() 
    elif self.proposal().proposer() == user:
      self.cancel()

  def is_expired(self):
    return sm.now() > self.proptime_row['expire_date']
    
  def cancel_time_only(self, missed_ping=None):
    self.proptime_row['current'] = False
    self.proptime_row['cancelled'] = True
    if missed_ping:
      self.proptime_row['missed_pings'] += 1
  
  def cancel(self, missed_ping=None):
    self.cancel_time_only(missed_ping)
    self.proposal().cancel_if_no_times() 
    
  def confirm_wait(self, start_now=True):
    if start_now:
      self.proptime_row['expire_date'] = sm.now() + datetime.timedelta(seconds=_seconds_left("requesting"))
      
  def update(self, port_time):
    self.proptime_row['start_now'] = port_time.start_now
    self.proptime_row['start_date'] = port_time.start_date
    self.proptime_row['duration'] = port_time.duration
    if port_time.start_now:
      self.confirm_wait()
    else:
      self.proptime_row['expire_date'] = port_time.expire_date
    self.proptime_row['current'] = True
    self.proptime_row['cancelled'] = False
    
  @staticmethod
  def add(prop_row, port_time):
    return ProposalTime(app_tables.proposal_times.add_row(proposal=prop_row,
                                                          start_now=port_time.start_now,
                                                          start_date=port_time.start_date,
                                                          duration=port_time.duration,
                                                          expire_date=port_time.expire_date,
                                                          current=True,
                                                          cancelled=False,
                                                          users_accepting=[],
                                                          jitsi_code="",
                                                          missed_pings=0,
                                                         )).confirm_wait(port_time.start_now)
  
  @staticmethod
  def get_by_id(time_id):
    return ProposalTime(app_tables.proposal_times.get_by_id(time_id))
  
  @staticmethod
  def none_left(prop_row):
    return len(app_tables.proposal_times.search(cancelled=False, proposal=prop_row))==0

  @staticmethod
  def rows_from_prop_row(prop_row, require_current=False):
    if require_current:
      return app_tables.proposal_times.search(current=True, proposal=prop_row)
    else:
      return app_tables.proposal_times.search(cancelled=False, proposal=prop_row)

  @staticmethod
  def get_now(user):
    current_proptime = ProposalTime.get_now_proposing(user)
    if not current_proptime:
      current_proptime = ProposalTime.get_now_accepting(user)
    if current_proptime:
      return current_proptime
    else:
      return None  
    
  @staticmethod
  def get_now_proposing(user):
    """Return user's current 'start_now' proposal_times row"""
    if DEBUG:
      print("get_now_proposal_time")
    current_prop_rows = Proposal.get_current_prop_rows(user)
    for prop_row in current_prop_rows:
      trial_get = app_tables.proposal_times.get(proposal=prop_row,
                                                current=True,
                                                start_now=True,
                                               )
      if trial_get:
        return ProposalTime(trial_get)
    return None

  @staticmethod
  def get_now_accepting(user):
    """Return user's current 'start_now' proposal_times row"""
    if DEBUG:
      print("_get_now_accept")
    proptime_row = app_tables.proposal_times.get(users_accepting=[user],
                                                 current=True,
                                                 start_now=True,
                                                )
    if proptime_row:
      return ProposalTime(proptime_row)
    else:
      return None

  
class Proposal():
  
  def __init__(self, prop_row):
    self.prop_row = prop_row

  def get_id(self):
    return self.prop_row.get_id()
    
  def portable(self, user):
    row_dict = dict(self.prop_row)
    row_dict['prop_id'] = self.get_id()
    proposer = row_dict.pop('user')
    row_dict['own'] = proposer == user
    row_dict['user'] = port.User.get(proposer)
    row_dict['times'] = [ProposalTime(row).portable() for row 
                         in ProposalTime.rows_from_prop_row(self.prop_row, require_current=True)]
    eligible_users = row_dict.pop('eligible_users')
    row_dict['eligible_users'] = [port.User.get(user) for user in eligible_users]
    assert row_dict['current']
    del row_dict['current']
    del row_dict['created']
    del row_dict['last_edited']
    return port.Proposal(**row_dict)

  def row(self):
    return self.prop_row
  
  def proposer(self):
    return self.prop_row['user']
  
  def is_visible(self, user):
    return sm.is_visible(self.prop_row['user'], user)

  def pinged_email(self): 
    sm.pinged_email(self.prop_row['user'])

  def cancel_if_no_times(self):
    if ProposalTime.none_left(self.prop_row):
      self.prop_row['current'] = False

  def update(self, port_prop):
    #self.prop_row['current'] = True
    self.prop_row['last_edited'] = sm.now()
    self.prop_row['eligible'] = port_prop.eligible
    self.prop_row['eligible_users'] = [app_tables.users.get_by_id(port_user.user_id) 
                                       for port_user in port_prop.eligible_users]
    self.prop_row['eligible_groups'] = port_prop.eligible_groups
    ## First cancel removed rows
    new_time_ids = [port_time.time_id for port_time in port_prop.times]
    for proptime_row in Proposal_Time.rows_from_prop_row(self.prop_row):     
      if proptime_row.get_id() not in new_time_ids:
        ProposalTime(proptime_row).cancel()
    ## Then update or add
    for port_time in port_prop.times:
      if port_time.time_id:
        ProposalTime.get_by_id(port_time.time_id).update(port_time)
      else:
        ProposalTime.add(prop_row=self.prop_row, port_time=port_time)
  
  @staticmethod
  def add(user, port_prop):
    now = sm.now()
    user_rows = [app_tables.users.get_by_id(port_user.user_id) for port_user in port_prop.eligible_users]
    new_prop_row = app_tables.proposals.add_row(user=user,
                                                current=True,
                                                created=now,
                                                last_edited=now,
                                                eligible=port_prop.eligible,
                                                eligible_users=user_rows,
                                                eligible_groups=port_prop.eligible_groups,
                                               )
    for port_time in port_prop.times:
      ProposalTime.add(prop_row=new_prop_row, port_time=port_time)
    return Proposal(new_prop_row)
  
  @staticmethod
  def get_by_id(prop_id):
    return Proposal(app_tables.proposals.get_by_id(prop_id))

  @staticmethod
  def get_current_prop_rows(user):
    return app_tables.proposals.search(user=user, current=True)
  
  @staticmethod
  def get_port_proposals(user):
    """Return list of Proposals visible to user
    
    Side effects: prune proposals
    """
    _prune_proposals()
    port_proposals = []
    for row in app_tables.proposals.search(current=True):
      prop = Proposal(row)
      if prop.is_visible(user):
        port_proposals.append(prop.portable(user))
    return port_proposals
