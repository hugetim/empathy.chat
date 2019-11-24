import anvil.tables
from anvil.tables import app_tables
import anvil.server
import datetime
import anvil.tz
import parameters as p
import server_misc as sm


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
  timeout = datetime.timedelta(seconds=p.WAIT_SECONDS + p.CONFIRM_MATCH_SECONDS + 2*p.BUFFER_SECONDS)
  cutoff_r = sm.now() - timeout
  old_requests = (r for r in app_tables.requests.search(current=True, match_id=None)
                    if r['last_confirmed'] < cutoff_r)
  for row in old_requests:
    row['current'] = False
  # below (matched separately) ensures that no ping requests left hanging by cancelling only one
  old_ping_requests = (r for r in app_tables.requests.search(current=True)
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
    
def _get_request_type(user):
  current_row = app_tables.requests.get(user=user, current=True)
  if current_row:
    return current_row['request_type']


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
  print ("('init')")
  sm.initialize_session()
  # Prune expired items for all users
  _prune_requests()
  _prune_matches()
  sm.prune_messages()
  # Initialize user info
  user = anvil.server.session['user']
  print (user['email'])
  trust_level, request_em, rem_opts, re_st, pinged_em = sm.get_user_info(user)
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
    status, seconds_left, tallies = _confirm_wait(user)
    request_type = _get_request_type(user)
  else:
    request_type = "will_offer_first"
  return test_mode, request_em, rem_opts, re_st, pinged_em, request_type, status, seconds_left, tallies, email_in_list, name


@anvil.server.callable
@anvil.tables.in_transaction
def confirm_wait(user_id=""):
  """updates last_confirmed for current request, returns _get_status(user)"""
  print("confirm_wait", user_id)
  user = sm.get_user(user_id)
  return confirm_wait_helper(user)


def confirm_wait_helper(user):
  """updates last_confirmed for current request, returns _get_status(user)"""
  current_row = app_tables.requests.get(user=user, current=True)
  if current_row:
    current_row['last_confirmed'] = sm.now()
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
  """
  current_row = app_tables.requests.get(user=user, current=True)
  status = None
  last_confirmed = None
  ping_start = None
  tallies = _get_tallies(user)
  if current_row:
    if current_row['match_id']:
      matched_request_confirms = [r['last_confirmed'] for r
                                  in app_tables.requests.search(match_id=current_row['match_id'],
                                                                current=True)]
      last_confirmed = min(matched_request_confirms)
      ping_start = current_row['ping_start']
      assert last_confirmed < ping_start
      if current_row['last_confirmed'] > last_confirmed:
        status = "pinging"
      else:
        status = "pinged"
    else:
      status = "requesting"
      last_confirmed = current_row['last_confirmed']
  else:
    # Note: 0 used for 'complete' field b/c False not allowed in SimpleObjects
    this_match = current_match(user)
    if this_match:
      status = "matched"
      ping_start = this_match['match_commence']
  return status, _seconds_left(status, last_confirmed, ping_start), tallies


def has_status(user):
  """
  returns Boolean(current_status)
  """
  current_row = app_tables.requests.get(user=user, current=True)
  if current_row:
    return True
  else:
    this_match = current_match(user)
    if this_match:
      return True
    else:
      return False


@anvil.server.callable
@anvil.tables.in_transaction
def get_tallies():
  """Return tallies dictionary

  Side effects: prune requests and request_em settings"""
  _prune_requests()
  user = anvil.server.session['user']
  return _get_tallies(user)


def _get_tallies(user):
  tallies =	dict(receive_first=0,
                 will_offer_first=0,
                 request_em=0)
  for row in app_tables.requests.search(current=True, match_id=None):
    user2 = row['user']
    if user2 != user and sm.is_visible(user2, user):
      tallies[row['request_type']] += 1
  tallies['request_em'] = len(sm.users_to_email_re_notif(user))
  return tallies


@anvil.server.callable
@anvil.tables.in_transaction
def get_code(user_id=""):
  """returns jitsi_code, request_type (or Nones)"""
  print("get_code", user_id)
  user = sm.get_user(user_id)
  current_row = app_tables.requests.get(user=user, current=True)
  code = None
  request_type = None
  if current_row:
    code = current_row['jitsi_code']
    request_type = current_row['request_type']
  else:
    # Note: 0 used for 'complete' field b/c False not allowed in SimpleObjects
    this_match, i = current_match_i(user)
    code = this_match['jitsi_code'] # assumes only one uncompleted for this user
    request_type = this_match['request_types'][i]
  return code, request_type


def _create_match(user, excluded=()):
  """attempt to create a match for user"""
  excluded_users = list(excluded)
  current_row = app_tables.requests.get(user=user, current=True)
  if current_row:
    request_type = current_row['request_type']
    if request_type == "will_offer_first":
      requests = [r for r in app_tables.requests.search(current=True,
                                                        match_id=None)
                  if (r['user'] not in [user] + excluded_users
                      and sm.is_visible(r['user'], user))]
    else:
      assert request_type == "receive_first"
      requests = [r for r in app_tables.requests.search(current=True,
                                                        request_type="will_offer_first",
                                                        match_id=None)
                  if (r['user'] not in [user] + excluded_users
                      and sm.is_visible(r['user'], user))]
    if requests:
      current_row['ping_start'] = sm.now()
      current_row['match_id'] = sm.new_match_id()
      current_row['jitsi_code'] = sm.new_jitsi_code()
      cms = [r['missed_pings'] for r in requests]
      eligible_requests = [r for r in requests if r['missed_pings'] == min(cms)]
      earliest_request = min(eligible_requests, key=lambda row: row['start'])
      earliest_request['ping_start'] = current_row['ping_start']
      earliest_request['match_id'] = current_row['match_id']
      earliest_request['jitsi_code'] = current_row['jitsi_code']
      lc = min(current_row['last_confirmed'],
               earliest_request['last_confirmed'])
      if (current_row['ping_start'] - lc).seconds <= p.BUFFER_SECONDS:
        _match_commenced(user)


def _create_matches(excluded=()):
  """attempt to create a match from existing requests, iterate"""
  excluded_users = list(excluded)
  # find top request in queue
  all_requests = [r for r in app_tables.requests.search(current=True,
                                                        match_id=None)
                    if r['user'] not in excluded_users]
  if all_requests:
    all_cms = [r['missed_pings'] for r in all_requests]
    all_eligible_requests = [r for r in all_requests if r['missed_pings'] == min(all_cms)]
    current_row = min(all_eligible_requests, key=lambda row: row['start'])
    user = current_row['user']
    # attempt to create a match for top request
    _create_match(user, excluded_users)
    # attempt to create matches for remaining requests
    _create_matches(excluded_users + [user])


@anvil.server.callable
@anvil.tables.in_transaction
def add_request(request_type, user_id=""):
  """
  return status, last_confirmed, ping_start, num_emailed
  """
  print("add_request", request_type, user_id)
  user = sm.get_user(user_id)
  return _add_request(user, request_type)


def _add_request(user, request_type):
  """
  return status, seconds_left, num_emailed
  """
  num_emailed = 0
  status, seconds_left, tallies = _get_status(user)
  assert status is None
  _add_request_row(user, request_type)
  _create_matches()
  status, seconds_left, tallies = _get_status(user)
  if status == "requesting":
    num_emailed = sm.request_emails(request_type)
  return status, seconds_left, num_emailed


def _cancel(user):
  current_row = app_tables.requests.get(user=user, current=True)
  if current_row:
    current_row['current'] = False
    if current_row['match_id']:
      matched_requests = app_tables.requests.search(match_id=current_row['match_id'],
                                                    current=True)
      for row in matched_requests:
        row['ping_start'] = None
        row['match_id'] = None
        row['jitsi_code'] = None
        if _seconds_left("requesting", row['last_confirmed']) <= 0:
          row['current'] = False
      current_row['missed_pings'] += 1
      _create_matches()
  return _get_tallies(user)


@anvil.server.callable
@anvil.tables.in_transaction
def cancel(user_id=""):
  """
  Remove request and cancel match (if applicable)
  Cancel any expired requests part of a cancelled match
  Returns tallies
  """
  print("cancel", user_id)
  user = sm.get_user(user_id)
  return _cancel(user)


def _cancel_other(user):
  current_row = app_tables.requests.get(user=user, current=True)
  if current_row:
    if current_row['match_id']:
      matched_requests = app_tables.requests.search(match_id=current_row['match_id'],
                                                    current=True)
      for row in matched_requests:
        row['ping_start'] = None
        row['match_id'] = None
        row['jitsi_code'] = None
        if row['user'] != user:
          row['missed_pings'] += 1
          row['current'] = False
        if _seconds_left("requesting", row['last_confirmed']) <= 0:
          row['current'] = False
      _create_matches()
  return _get_status(user)


@anvil.server.callable
@anvil.tables.in_transaction
def cancel_other(user_id=""):
  """
  return new status
  Upon failure of other to confirm match
  cancel match (if applicable)--and cancel their request
  Cancel any other expired requests part of a cancelled match
  """
  print("cancel_other", user_id)
  user = sm.get_user(user_id)
  return _cancel_other(user)


@anvil.server.callable
@anvil.tables.in_transaction
def match_commenced(user_id=""):
  """
  Returns _get_status(user)
  Upon first commence, copy row over and delete "matching" row.
  Should not cause error if already commenced
  """
  print("match_commenced", user_id)
  user = sm.get_user(user_id)
  return _match_commenced(user)


def _match_commenced(user):
  """
  Returns _get_status(user)
  Upon first commence, copy row over and delete "matching" row.
  Should not cause error if already commenced
  """
  current_row = app_tables.requests.get(user=user, current=True)
  if current_row:
    if current_row['match_id']:
      matched_requests = app_tables.requests.search(match_id=current_row['match_id'],
                                                    current=True)
      match_start = sm.now()
      new_match = app_tables.matches.add_row(users=[],
                                             request_types=[],
                                             match_id=current_row['match_id'],
                                             jitsi_code=current_row['jitsi_code'],
                                             match_commence=match_start,
                                             complete=[])
      for row in matched_requests:
        new_match['users'] += [row['user']]
        new_match['request_types'] += [row['request_type']]
        # Note: 0 used for 'complete' b/c False not allowed in SimpleObjects
        new_match['complete'] += [0]
        row['current'] = False
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


def _add_request_row(user, request_type):
  now = sm.now()
  new_row = app_tables.requests.add_row(user=user,
                                        current=True,
                                        request_type=request_type,
                                        start=now,
                                        last_confirmed=now,
                                        missed_pings=0
                                       )
  return new_row


def current_match(user):
  this_match = None
  current_matches = app_tables.matches.search(users=[user], complete=[0])
  for row in current_matches:
    i = row['users'].index(user)
    if row['complete'][i] == 0:
      this_match = row
  return this_match


def current_match_i(user):
  this_match = None
  current_matches = app_tables.matches.search(users=[user], complete=[0])
  for row in current_matches:
    i = row['users'].index(user)
    if row['complete'][i] == 0:
      this_match = row
  return this_match, i
