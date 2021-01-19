import anvil.tables
from anvil.tables import app_tables
import anvil.tables.query as q
import anvil.server
import datetime
import anvil.tz
from . import parameters as p
from . import server_misc as sm
from .timeproposals import Proposal, ProposalTime


TEST_TRUST_LEVEL = 10
DEBUG = False


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
                                                    jitsi_code=None,
                                                    expire_date=q.less_than(now),
                                                   )
  for row in old_prop_times:
    row['current'] = False
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
                                                         jitsi_code=q.not_(None),
                                                         accept_date=q.less_than(cutoff_r)
                                                        )
  if DEBUG:
    print("old_ping_prop_times2")
  for row in old_ping_prop_times:
    if DEBUG:
      print("old_ping_prop_times3")
    row['current'] = False
    if DEBUG:
      print("old_ping_prop_times4")
    proposals_to_check.add(row['proposal'])
  # now proposals, after proposal times so they get removed if all times are
  if DEBUG:
    print("old_proposals")
  for row in proposals_to_check:
    if DEBUG:
      print("old_proposals2")
    if len(app_tables.proposal_times.search(current=True, proposal=row))==0:
      if DEBUG:
        print("old_proposals3")
      row['current'] = False

    
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


@anvil.server.callable
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


def get_now_proposal_time(user):
  """Return user's current 'start_now' proposal_times row"""
  if DEBUG:
    print("get_now_proposal_time")
  current_proposals = app_tables.proposals.search(user=user, current=True)
  for prop in current_proposals:
    trial_get = app_tables.proposal_times.get(proposal=prop,
                                              current=True,
                                              start_now=True,
                                             )
    if trial_get:
      return trial_get
  return None


def _get_now_accept(user):
  """Return user's current 'start_now' proposal_times row"""
  if DEBUG:
    print("_get_now_accept")
  return app_tables.proposal_times.get(users_accepting=[user],
                                       current=True,
                                       start_now=True
                                      )


@anvil.server.callable
@anvil.tables.in_transaction
def confirm_wait(user_id=""):
  """updates expire_date for current request, returns _get_status(user)"""
  print("confirm_wait", user_id)
  user = sm.get_user(user_id)
  return confirm_wait_helper(user)


def confirm_wait_helper(user):
  """updates expire_date for current request, returns _get_status(user)"""
  if DEBUG:
    print("confirm_wait_helper")
  current_row = get_now_proposal_time(user)
  if current_row:
    current_row['expire_date'] = sm.now() + datetime.timedelta(seconds=_seconds_left("requesting"))
  return _get_status(user)


@anvil.server.callable
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
  current_row = get_now_proposal_time(user)
  expire_date = None
  ping_start = None
  proposals = []
  if current_row and current_row['start_now']:
    expire_date = current_row['expire_date']
    if current_row['jitsi_code']:
      status = "pinged"
      ping_start = current_row['accept_date']
    else:
      status = "requesting"
      proposals = _get_proposals(user)
  else:
    current_accept = _get_now_accept(user)
    if current_accept and current_accept['jitsi_code']:
      status = "pinging"
      ping_start = current_accept['accept_date']
      expire_date = current_accept['expire_date']
    else:
      this_match = current_match(user)
      if this_match:
        status = "matched"
        ping_start = this_match['match_commence']
      else:
        status = None
        proposals = _get_proposals(user)
  return {'status': status, 
          'seconds_left': _seconds_left(status, expire_date, ping_start), 
          'proposals': proposals,
         }


def has_status(user):
  """
  returns bool(current_status)
  """
  current_row = get_now_proposal_time(user)
  if current_row:
    return True
  else:
    current_accept = _get_now_accept(user)
    if current_accept:
       return True
    else:
      this_match = current_match(user)
      if this_match:
        return True
  return False


def _get_proposals(user):
  """Return list of Proposals visible to user
  
  Side effects: prune proposals
  """
  _prune_proposals()
  proposals = []
  for row in app_tables.proposals.search(current=True):
    if _proposal_is_visible(row, user):
      proposals.append(_proposal(row, user))
  return proposals


def _proposal(proposal_row, user):
  """Convert proposal_times row into a row for the client dashboard"""
  if DEBUG:
    print("_proposal")
  proposer = proposal_row['user']
  own = proposer == user
  times = [_proposal_time(row) for row 
           in app_tables.proposal_times.search(current=True, proposal=proposal_row)]
  return Proposal(prop_id=proposal_row.get_id(),  own=own, name=proposer['name'],
                  times=times, eligible=proposal_row['eligible'],
                  eligible_users=proposal_row['eligible_users'], eligible_groups=proposal_row['eligible_groups'],
                 )

def _proposal_time(prop_time_row):
  return ProposalTime(time_id=prop_time_row.get_id(), 
                      start_now=prop_time_row['start_now'], start_date=prop_time_row['start_date'],
                      duration=prop_time_row['duration'], expire_date=prop_time_row['expire_date'],)


def _proposal_is_visible(proposal, user):
  return sm.is_visible(proposal['user'], user)


@anvil.server.callable
@anvil.tables.in_transaction
def get_code(user_id=""):
  """Return jitsi_code, duration (or Nones)"""
  print("get_code", user_id)
  user = sm.get_user(user_id)
  
  current_row = get_now_proposal_time(user)
  if current_row:
    return current_row['jitsi_code'], current_row['duration']
  else:
    current_accept = _get_now_accept(user)
    if current_accept:
       return current_accept['jitsi_code'], current_accept['duration']
    else:
      this_match = current_match(user)
      if this_match:
        prop_time = this_match['proposal_time']
        return prop_time['jitsi_code'], prop_time['duration']
  return None, None


@anvil.server.callable
@anvil.tables.in_transaction
def accept_proposal(proptime_id, user_id=""):
  """Return _get_status
  
  Side effect: update proptime table with acceptance, if available
  """
  print("accept_proposal", proptime_id, user_id)
  user = sm.get_user(user_id)
  return _attempt_accept_proposal(user, proptime_id)


def _remove_proposal_time_row(proposal_time_row):
  proposal_time_row['current'] = False
  proposal_time_row['cancelled'] = True
  proposal_row = proposal_time_row['proposal']
  if len(app_tables.proposal_times.search(current=True, proposal=proposal_row))==0:
    proposal_row['current'] = False

    
def _accept_proposal(user, proptime, status):
  if DEBUG:
    print("_accept_proposal")
  now = sm.now()
  if status == "requesting":
    own_now_proposal_time = get_now_proposal_time(user)
    if own_now_proposal_time:
      _remove_proposal_time_row(own_now_proposal_time)
  proposal = proptime['proposal']
  proptime['users_accepting'] = [user]
  proptime['accept_date'] = now
  proptime['jitsi_code'] = sm.new_jitsi_code()
  if (proptime['expire_date'] - datetime.timedelta(seconds=_seconds_left("requesting")) 
                              - now).seconds <= p.BUFFER_SECONDS:
    _match_commenced(user)
  else:
    sm.pinged_email(proposal['user'])


def _attempt_accept_proposal(user, proptime_id):
  if DEBUG:
    print("_attempt_accept_proposal")
  state = _get_status(user)
  status = state['status']
  if status in [None, "requesting"]:
    proptime = app_tables.proposal_times.get_by_id(proptime_id)
    if proptime['current'] and (not proptime['users_accepting']) and _proposal_is_visible(proptime['proposal'], user):
      _accept_proposal(user, proptime, status)
  return _get_status(user)


@anvil.server.callable
@anvil.tables.in_transaction
def add_proposal(proposal, user_id=""):
  """Return _get_status
  
  Side effect: Update proposal tables with additions, if valid
  """
  print("add_proposal", user_id)
  user = sm.get_user(user_id)
  state, prop_id = _add_proposal(user, proposal)
  return state


def _add_proposal(user, proposal):
  state = _get_status(user)
  status = state['status']
  if status is None or not proposal.times[0].start_now:
    prop_id = _add_proposal_rows(user, proposal)
  else:
    prop_id = None
  return _get_status(user), prop_id


def _add_proposal_rows(user, proposal):
  now = sm.now()
  new_prop_row = app_tables.proposals.add_row(user=user,
                                              current=True,
                                              created=now,
                                              last_edited=now,
                                              eligible=proposal.eligible,
                                              eligible_users=proposal.eligible_users,
                                              eligible_groups=proposal.eligible_groups,
                                             )
  for time in proposal.times:
    _add_proposal_time(prop_row=new_prop_row, prop_time=time)
  return new_prop_row.get_id()


def _add_proposal_time(prop_row, prop_time):
  expire_date=prop_time.expire_date
  assert expire_date is not None
  new_time = app_tables.proposal_times.add_row(proposal=prop_row,
                                               start_now=bool(prop_time.start_now),
                                               start_date=prop_time.start_date,
                                               duration=prop_time.duration,
                                               expire_date=expire_date,
                                               current=True,
                                               cancelled=False,
                                               missed_pings=0,
                                              )

  
@anvil.server.callable
@anvil.tables.in_transaction
def edit_proposal(proposal, user_id=""):
  """Return _get_status
  
  Side effect: Update proposal tables with revision, if valid
  """
  print("edit_proposal", user_id)
  user = sm.get_user(user_id)
  return _edit_proposal(user, proposal)


def _edit_proposal(user, proposal):
  print("Not yet preventing editing to make multiple now proposals")
  prop_id = _edit_proposal_rows(user, proposal)
  return _get_status(user)


def _edit_proposal_rows(user, proposal):
  prop_row = app_tables.proposals.get_by_id(proposal.prop_id)
  prop_row['current'] = True
  prop_row['last_edited'] = sm.now()
  prop_row['eligible'] = proposal.eligible
  prop_row['eligible_users'] = proposal.eligible_users
  prop_row['eligible_groups'] = proposal.eligible_groups
  ## First cancel removed rows
  new_time_ids = [time.time_id for time in proposal.times]
  for row in app_tables.proposal_times.search(current=True, proposal=prop_row):
    if row.get_id() not in new_time_ids:
      row['current'] = False
      row['cancelled'] = True
  for time in proposal.times:
    _edit_proposal_time(prop_row=prop_row, prop_time=time)


def _edit_proposal_time(prop_row, prop_time):
  expire_date=prop_time.expire_date
  assert expire_date is not None
  time_row = app_tables.proposal_times.get_by_id(prop_time.time_id)
  if time_row:
    time_row['start_now'] = bool(prop_time.start_now)
    time_row['start_date'] = prop_time.start_date
    time_row['duration'] = prop_time.duration
    time_row['expire_date'] = expire_date
    time_row['current'] = True
    time_row['cancelled'] = False
  else:
    _add_proposal_time(prop_row, prop_time)

    
def _cancel(user, proptime_id=None):
  if DEBUG:
    print("_cancel", proptime_id)
  if proptime_id:
    current_row = app_tables.proposal_times.get_by_id(proptime_id)
  else:
    current_row = get_now_proposal_time(user)
    if not current_row:
      current_row = _get_now_accept(user)
      if DEBUG:
        print("_cancel here1")
  if current_row:
    if DEBUG:
      print("_cancel here2")
    if current_row['users_accepting'] and user in current_row['users_accepting']:
      if DEBUG:
        print("_cancel here3")
      _remove_user_accepting(user, current_row)
      if sm.now() > current_row['expire_date']:
        _remove_proposal_time_row(current_row)
    elif user == current_row['proposal']['user']:
      _remove_proposal_time_row(current_row)
  return _get_status(user)


def _remove_user_accepting(user, proposal_time):
  # below code assumes only dyads allowed
  proposal_time['users_accepting'] = None
  proposal_time['accept_date'] = None
  proposal_time['jitsi_code'] = None

  
@anvil.server.callable
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
    current_row = app_tables.proposal_times.get_by_id(proptime_id)
  else:
    current_row = get_now_proposal_time(user)
    if not current_row:
      current_row = _get_now_accept(user)
  if current_row:
    if current_row['users_accepting'] and user in current_row['users_accepting']:
      _remove_proposal_time_row(current_row)
      current_row['missed_pings'] += 1
    elif user == current_row['proposal']['user']:
      # below code assumes only dyads allowed
      current_row['users_accepting'] = None
      current_row['accept_date'] = None
      current_row['jitsi_code'] = None
      if sm.now() > current_row['expire_date']:
        _remove_proposal_time_row(current_row)
  return _get_status(user)


@anvil.server.callable
@anvil.tables.in_transaction
def cancel_other(proptime_id=None, user_id=""):
  """Return new _get_status
  Upon failure of other to confirm match
  cancel match (if applicable)--and cancel their request
  """
  print("cancel_other", proptime_id, user_id)
  user = sm.get_user(user_id)
  return _cancel_other(user, proptime_id)


@anvil.server.callable
@anvil.tables.in_transaction
def match_commenced(proptime_id=None, user_id=""):
  """Return _get_status(user)
  Upon first commence, copy row over and delete "matching" row.
  Should not cause error if already commenced
  """
  print("match_commenced", proptime_id, user_id)
  user = sm.get_user(user_id)
  return _match_commenced(user, proptime_id)


def _match_commenced(user, proptime_id):
  """Return _get_status(user)
  Upon first commence, copy row over and delete "matching" row.
  Should not cause error if already commenced
  """
  if DEBUG:
    print("_match_commenced")
  if proptime_id:
    print("proptime_id")
    current_row = app_tables.proposal_times.get_by_id(proptime_id)
  else:
    current_row = get_now_proposal_time(user)
    if not current_row:
      print("not current_row")
      current_row = _get_now_accept(user)
  if current_row:
    print("current_row")
    if current_row['jitsi_code']:
      print("'jitsi_code'")
      match_start = sm.now()
      users = [current_row['proposal']['user']] + list(current_row['users_accepting'])
      new_match = app_tables.matches.add_row(users=users,
                                             proposal_time=current_row,
                                             match_commence=match_start,
                                             complete=[0]*len(users))
      # Note: 0 used for 'complete' b/c False not allowed in SimpleObjects
      _remove_proposal_time_row(current_row)
  return _get_status(user)


@anvil.server.callable
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
