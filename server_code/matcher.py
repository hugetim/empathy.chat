import anvil.tables
from anvil.tables import app_tables
import anvil.server
import datetime
import anvil.tz
from . import parameters as p
from . import server_misc as sm
from .portable import DashProposal


TEST_TRUST_LEVEL = 10


def _seconds_left(status, last_confirmed, ping_start=None):
  if status in ["pinging", "pinged"]:
    if ping_start:
      confirm_match = p.CONFIRM_MATCH_SECONDS - (sm.now() - ping_start).seconds
    else:
      confirm_match = p.CONFIRM_MATCH_SECONDS
    if status == "pinging":
      return confirm_match + 2*p.BUFFER_SECONDS # accounts for delay in response arriving
    elif status == "pinged":
      return confirm_match + p.BUFFER_SECONDS # accounts for delay in ping arriving
  elif status == "requesting":
    if last_confirmed:
      return p.WAIT_SECONDS - (sm.now() - last_confirmed).seconds
    else:
      return p.WAIT_SECONDS
  elif status in [None, "matched"]:
    return None
  else:
    print("matcher.seconds_left(s,lc,ps): " + status)


def _prune_requests():
  """Prune definitely outdated requests, unmatched then matched"""
  now = sm.now()
  old_requests = (r for r in app_tables.proposal_times.search(current=True, match_id=None)
                    if r['expire_date'] < now)
  for row in old_requests:
    row['current'] = False
  # below (matched separately) ensures that no ping requests left hanging by cancelling only one
  timeout = datetime.timedelta(seconds=p.WAIT_SECONDS + p.CONFIRM_MATCH_SECONDS + 2*p.BUFFER_SECONDS)
  cutoff_r = now - timeout
  old_ping_requests = (r for r in app_tables.proposal_times.search(current=True, start_now=True)
                       if (r['match_id'] is not None and r['ping_start'] < cutoff_r))
  for row in old_ping_requests:
    row['current'] = False


def _prune_matches():
  """Complete old commenced matches for all users"""
  assume_complete = datetime.timedelta(hours=4)
  cutoff_m = sm.now() - assume_complete
  # Note: 0 used for 'complete' field b/c False not allowed in SimpleObjects
  old_matches = (m for m in app_tables.matches.search(complete=[0])
                 if m['match_commence'] < cutoff_m)
  for row in old_matches:
    temp = row['complete']
    for i in range(len(temp)):
      # Note: 1 used for 'complete' field b/c True not allowed in SimpleObjects
      temp[i] = 1
    row['complete'] = temp

                  
#def _get_request_type(user):
#  current_row = app_tables.requests.get(user=user, current=True)
#  if current_row:
#    return current_row['request_type']


@anvil.server.callable
@anvil.tables.in_transaction
def init():
  """
  Assumed to run upon initializing Form1
  returns trust_level, request_em, pinged_em, current_status, ref_time (or None),
          tallies, alt_avail, email_in_list
  prunes old requests/offers/matches
  updates last_confirmed if currently requesting/ping
  """
  print("('init')")
  sm.initialize_session()
  # Prune expired items for all users
  _prune_requests()
  _prune_matches()
  sm.prune_messages()
  # Initialize user info
  user = anvil.server.session['user']
  print(user['email'])
  trust_level, pinged_em = sm.get_user_info(user)
  email_in_list = None
  name = None
  if trust_level == 0:
    email_in_list = sm.email_in_list(user)
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
  status, seconds_left, tallies = _get_status(user)
  if status == 'pinged' and seconds_left <= 0:
    status, seconds_left, tallies = _cancel(user)
  elif status == 'pinged':
    status, seconds_left, tallies = _match_commenced(user)
  elif status == 'pinging' and seconds_left <= 0:
    status, seconds_left, tallies = _cancel_other(user)
  if status in ('requesting', 'pinged', 'pinging'):
    status, seconds_left, tallies = confirm_wait_helper(user)
    #request_type = _get_request_type(user)
  else:
    request_type = "will_offer_first"
  return test_mode, pinged_em, request_type, status, seconds_left, tallies, email_in_list, name


def _get_now_proposal_time(user):
  """Return user's current 'start_now' proposal_times row"""
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
  return app_tables.proposal_times.get(user_accepting=user,
                                       current=True,
                                      )


@anvil.server.callable
@anvil.tables.in_transaction
def confirm_wait(user_id=""):
  """updates last_confirmed for current request, returns _get_status(user)"""
  print("confirm_wait", user_id)
  user = sm.get_user(user_id)
  return confirm_wait_helper(user)


def confirm_wait_helper(user):
  """updates last_confirmed for current request, returns _get_status(user)"""  
  current_row = _get_now_proposal_time(user)
  if current_row:
    current_row['expire_date'] = sm.now() + datetime.timedelta(seconds=p.WAIT_SECONDS)
  status, seconds_left, tallies = _get_status(user)
  return status, seconds_left, tallies


@anvil.server.callable
@anvil.tables.in_transaction
def get_status(user_id=""):
  user = sm.get_user(user_id)
  return _get_status(user)


def _get_status(user):
  """
  returns current_status, last_confirmed, ping_start, tallies
  last_confirmed: min of this or other's last_confirmed
  ping_start: ping_start or, for "matched", match_commence
  assumes 2-person matches only
  assumes now proposals only
  """
  current_row = _get_now_proposal_time(user)
  status = None
  expire_date = None
  ping_start = None
  tallies = _get_tallies(user)
  if current_row:
    if current_row['match_id']:
      status = "pinged"
      ping_start = current_row['ping_start']
    else:
      status = "requesting"
    expire_date = current_row['expire_date']
  else:
    current_accept = _get_now_accept(user)
    if current_accept:
      status = "pinging"
      ping_start = current_accept['ping_start']
      expire_date = current_accept['expire_date']
    else:
      this_match = current_match(user)
      if this_match:
        status = "matched"
        ping_start = this_match['match_commence']
  return status, _seconds_left(status, expire_date, ping_start), tallies


def has_status(user):
  """
  returns bool(current_status)
  """
  current_row = _get_now_proposal_time(user)
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


@anvil.server.callable
@anvil.tables.in_transaction
def get_tallies():
  """Return list of DashProposals
  
  Side effects: prune requests and request_em settings
  """
  _prune_requests()
  user = anvil.server.session['user']
  return _get_tallies(user)


def _get_tallies(user):
  return [_dash_proposal(row, user)
          for row in app_tables.proposal_times.search(current=True, match_id=None)
                  if _proposal_is_visible(row['proposal'], user)
         ]


def _dash_proposal(proposal_time, user):
  """Convert proposal_times row into a row for the client dashboard"""
  proposal = proposal_time['proposal']
  proposer = proposal['user']
  own = proposer == user
  return DashProposal(prop_id=proposal.get_id(), time_id=proposal_time.get_id(), own=own, name=proposer['name'],
                      start_now=proposal_time['start_now'], start_date=proposal_time['start_date'],
                      duration=proposal_time['duration'], expire_date=proposal_time['expire_date'],
                     )


def _proposal_is_visible(proposal, user):
  return sm.is_visible(proposal['user'], user)


@anvil.server.callable
@anvil.tables.in_transaction
def get_code(user_id=""):
  """returns jitsi_code, duration (or Nones)"""
  print("get_code", user_id)
  user = sm.get_user(user_id)
  
  current_row = _get_now_proposal_time(user)
  if current_row:
    return current_row['jitsi_code'], current_row['duration']
  else:
    current_accept = _get_now_accept(user)
    if current_accept:
       return current_accept['jitsi_code'], current_accept['duration']
    else:
      this_match = current_match(user)
      if this_match:
        return this_match['jitsi_code'], this_match['duration']
  return None, None


@anvil.server.callable
@anvil.tables.in_transaction
def accept_proposal(proptime_id, user_id=""):
  """Return status, seconds_left, tallies
  
  Side effect: update proptime table with acceptance, if available
  """
  print("accept_proposal", proptime_id, user_id)
  user = sm.get_user(user_id)
  return _attempt_accept_proposal(user, proptime_id)


def _accept_proposal(user, proptime, status):
  if status == "requesting":
    own_now_proposal = _get_now_proposal_time(user)
    if own_now_proposal:
      own_now_proposal['current'] = False
  proposal = proptime['proposal']
  proptime['user_accepting'] = user
  proptime['ping_start'] = sm.now()
  proptime['match_id'] = sm.new_match_id()
  proptime['jitsi_code'] = sm.new_jitsi_code()
  if (proptime['expire_date'] - datetime.timedelta(seconds=p.WAIT_SECONDS) 
                              - proptime['ping_start']).seconds <= p.BUFFER_SECONDS:
    _match_commenced(user)
  else:
    sm.pinged_email(proposal['user'])


def _attempt_accept_proposal(user, proptime_id):
  status, seconds_left, tallies = _get_status(user)
  if status in [None, "requesting"]:
    proptime = app_tables.proposal_times.get_by_id(proptime_id)
    if proptime['current'] and (proptime['user_accepting'] is None) and _proposal_is_visible(proptime['proposal'], user):
      _accept_proposal(user, proptime, status)
  return _get_status(user)


@anvil.server.callable
@anvil.tables.in_transaction
def add_request(prop_dict, user_id=""):
  """Return status, seconds_left, tallies
  
  Side effect: Update proposal tables with additions, if valid
  """
  print("add_request", prop_dict, user_id)
  user = sm.get_user(user_id)
  return _add_request(user, prop_dict)


def _add_request(user, prop_dict):
  status, seconds_left, tallies = _get_status(user)
  if status is None:
    _add_request_rows(user, prop_dict)
  return _get_status(user)


def _add_request_rows(user, prop_dict):
  now = sm.now()
  new_proposal = app_tables.proposals.add_row(user=user,
                                              current=True,
                                              request_type=request_type,
                                              created=now,
                                              last_edited=now,
                                              eligible=prop_dict['eligible'],
                                              eligible_users=prop_dict['eligible_users'],
                                              eligible_groups=prop_dict['eligible_groups'],
                                             )
  _add_proposal_time(proposal=new_proposal,
                     start_now=prop_dict['start_now'],
                     start_date=prop_dict['start_date'],
                     duration=prop_dict['duration'],
                     expire_date=prop_dict['start_date']-prop_dict['cancel_buffer'],
                    )
  for alt_time in prop_dict['alt']:
    _add_proposal_time(proposal=new_proposal,
                       start_now=alt_time['start_now'],
                       start_date=alt_time['start_date'],
                       duration=alt_time['duration'],
                       expire_date=alt_time['start_date']-alt_time['cancel_buffer'],
                      )
  return new_proposal


def _add_proposal_time(proposal, start_now, start_date, duration, expire_date):
  new_time = app_tables.proposal_times.add_row(proposal=proposal,
                                               start_now=start_now,
                                               start_date=start_date,
                                               duration=duration,
                                               expire_date=expire_date,
                                               current=True,
                                               missed_pings=0,
                                              )
  
    
def _cancel(user, proptime_id):
  current_row = app_tables.proposal_times.get_by_id(proptime_id)
  if current_row:
    if user == current_row['user_accepting']:
      current_row['user_accepting'] = None
      current_row['ping_start'] = None
      current_row['match_id'] = None
      current_row['jitsi_code'] = None
      if sm.now() > current_row['expire_date']:
        current_row['current'] = False
    elif user == current_row[proposal][user]:
      current_row['current'] = False
  return _get_tallies(user)


@anvil.server.callable
@anvil.tables.in_transaction
def cancel(proptime_id, user_id=""):
  """Remove proptime and cancel pending match (if applicable)
  Return tallies
  """
  print("cancel", proptime_id, user_id)
  user = sm.get_user(user_id)
  return _cancel(user, proptime_id)


def _cancel_other(user, proptime_id):
  current_row = app_tables.proposal_times.get_by_id(proptime_id)
  if current_row:
    if user == current_row['user_accepting']:
      current_row['current'] = False
      row['missed_pings'] += 1
    elif user == current_row[proposal][user]:      
      current_row['user_accepting'] = None
      current_row['ping_start'] = None
      current_row['match_id'] = None
      current_row['jitsi_code'] = None
      if sm.now() > current_row['expire_date']:
        current_row['current'] = False
  return _get_status(user)


@anvil.server.callable
@anvil.tables.in_transaction
def cancel_other(proptime_id, user_id=""):
  """Return new status
  Upon failure of other to confirm match
  cancel match (if applicable)--and cancel their request
  Cancel any other expired requests part of a cancelled match
  """
  print("cancel_other", proptime_id, user_id)
  user = sm.get_user(user_id)
  return _cancel_other(user, proptime_id)


@anvil.server.callable
@anvil.tables.in_transaction
def match_commenced(proptime_id, user_id=""):
  """Returns _get_status(user)
  Upon first commence, copy row over and delete "matching" row.
  Should not cause error if already commenced
  """
  print("match_commenced", proptime_id, user_id)
  user = sm.get_user(user_id)
  return _match_commenced(user, proptime_id)


def _match_commenced(user, proptime_id):
  """Returns _get_status(user)
  Upon first commence, copy row over and delete "matching" row.
  Should not cause error if already commenced
  """
  current_row = app_tables.proposal_times.get_by_id(proptime_id)
  if current_row:
    if current_row['match_id']:
      match_start = sm.now()
      users = [current_row['proposal'][user], current_row['accepting_user']]
      new_match = app_tables.matches.add_row(users=users,
                                             duration=current_row['duration'],
                                             match_id=current_row['match_id'],
                                             jitsi_code=current_row['jitsi_code'],
                                             match_commence=match_start,
                                             complete=[0]*len(users))
      # Note: 0 used for 'complete' b/c False not allowed in SimpleObjects
      current_row['current'] = False
  return _get_status(user)


@anvil.server.callable
@anvil.tables.in_transaction
def match_complete(user_id=""):
  """Switch 'complete' to true in matches table for user, return tallies."""
  print("match_complete", user_id)
  user = sm.get_user(user_id)
  # Note: 0/1 used for 'complete' b/c Booleans not allowed in SimpleObjects
  this_match, i = current_match_i(user)
  temp = this_match['complete']
  temp[i] = 1
  this_match['complete'] = temp
  return _get_tallies(user)


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
