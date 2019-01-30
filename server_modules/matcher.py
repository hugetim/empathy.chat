import anvil.google.auth, anvil.google.drive, anvil.google.mail
from anvil.google.drive import app_files
import anvil.email
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.users
import anvil.server
import random
import datetime
import uuid
import anvil.tz
import parameters as p
import re
import helper as h


def _now():
  """return utcnow"""
  return datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc())


def _prune_requests():
<<<<<<< HEAD
  """Prune definitely outdated requests, unmatched then matched"""
  timeout = datetime.timedelta(seconds=2*p.CONFIRM_WAIT_SECONDS + p.CONFIRM_MATCH_SECONDS + p.BUFFER_SECONDS)
  cutoff_r = datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc()) - timeout
||||||| merged common ancestors
  'Prune definitely outdated requests, unmatched then matched'
  timeout = datetime.timedelta(seconds=2*p.CONFIRM_WAIT_SECONDS + p.CONFIRM_MATCH_SECONDS + p.BUFFER_SECONDS)
  cutoff_r = datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc()) - timeout
=======
  """Prune definitely outdated requests, unmatched then matched"""
  timeout = datetime.timedelta(seconds=p.WAIT_SECONDS + p.CONFIRM_MATCH_SECONDS + p.BUFFER_SECONDS)
  cutoff_r = _now() - timeout
>>>>>>> refactor-state
  old_requests = (r for r in app_tables.requests.search(current=True, match_id=None)
                    if r['last_confirmed'] < cutoff_r)
  for row in old_requests:
    row['current'] = False
  # below (matched separately) ensures that no ping requests left hanging by cancelling only one
  old_ping_requests = (r for r in app_tables.requests.search(current=True)
                       if (r['match_id'] is not None and r['ping_start'] < cutoff_r))
  for row in old_ping_requests:
    row['current'] = False


def _get_request_type(user):
  current_row = app_tables.requests.get(user=user, current=True)
  if current_row:
    return current_row['request_type']


@anvil.server.callable
@anvil.tables.in_transaction
def prune(user_id):
  """
  Assumed to run upon initializing Form1
  returns trust_level, request_em, match_em, current_status, ref_time (or None),
          tallies, alt_avail, email_in_list
  prunes old requests/offers
<<<<<<< HEAD
  updates last_confirmed if currently requesting/offering/pinged
  """
  assume_complete = datetime.timedelta(hours=4) 
||||||| merged common ancestors
  updates last_confirmed if currently requesting/offering/pinged
  '''
  assume_complete = datetime.timedelta(hours=4) 
=======
  updates last_confirmed if currently requesting/ping
  """
  assume_complete = datetime.timedelta(hours=4)
>>>>>>> refactor-state
  _initialize_session(user_id)
  user = anvil.server.session['user']
  # Prune requests, including from this user
  _prune_requests()
  # Complete old commenced matches for this user
  cutoff_m = _now() - assume_complete
  old_matches = (m for m in app_tables.matches.search(users=[user], complete=[0])
                   if m['match_commence'] < cutoff_m)
  for row in old_matches:
    i = row['users'].index(user)
    temp = row['complete']
    temp[i] = 1
    row['complete'] = temp
  # Return after confirming wait
  trust_level, request_em, match_em = get_user_info(user_id)
  email_in_list = None
  if trust_level == 0:
    email_in_list = _email_in_list(user['email'])
    if email_in_list:
      trust_level = 1
      user['trust_level'] = trust_level
    else:
      user['enabled'] = False
  status, lc, ps, tallies = _get_status(user)
  if status in ('pinged-one', 'pinged-mult', 'pinging-one', 'pinging-mult'):
    seconds_left = h.seconds_left(status, lc, ps)
    if status == 'pinged-mult' and seconds_left <= 0:
      status, lc, ps, tallies = _cancel_match(user)
    elif status in ('pinged-one', 'pinged-mult'):
      status, lc, ps, tallies = _match_commenced(user)
    elif status in ('pinging-one', 'pinging-mult') and seconds_left <= 0:
      status, lc, ps, tallies = _cancel_other(user)
  if status in ('requesting', 'requesting-confirm', 'pinged-one', 'pinged-mult',
                'pinging-one', 'pinging-mult'):
    status, lc, ps, tallies = _confirm_wait(user)
    request_type = _get_request_type(user)
  else:
    request_type = "will_offer_first"
  return trust_level, request_em, match_em, request_type, status, lc, ps, tallies, email_in_list


def _initialize_session(user_id):
  """initialize session state: user_id, user, and current_row"""
  anvil.server.session['user_id'] = user_id
  user = app_tables.users.get_by_id(user_id)
  anvil.server.session['user'] = user
  anvil.server.session['test_record'] = None


def _get_user(user_id):
  if anvil.server.session['user_id'] == user_id:
    return anvil.server.session['user']
  else:
    return app_tables.users.get_by_id(user_id)


def _email_in_list(email):
  sheet = app_files._2018_integration_program['Sheet1']
  for row in sheet.rows:
    if _emails_equal(email, row['email']):
      return True
  return False


def _emails_equal(a, b):
  em_re = re.compile(r"^([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)$")
  a_match = em_re.search(a)
  b_match = em_re.search(b)
  return a_match.group(1) == b_match.group(1) and a_match.group(2).lower() == b_match.group(2).lower()


@anvil.server.callable
@anvil.tables.in_transaction
def confirm_wait(user_id):
<<<<<<< HEAD
  _confirm_wait(user_id)
  
  
def _confirm_wait(user_id):
  """updates last_confirmed for current request"""
  user = app_tables.users.get_by_id(user_id)
||||||| merged common ancestors
  _confirm_wait(user_id)
  
  
def _confirm_wait(user_id):
  '''updates last_confirmed for current request'''
  user = app_tables.users.get_by_id(user_id)
=======
  """updates last_confirmed for current request, returns _get_status(user)"""
  user = _get_user(user_id)
  return _confirm_wait(user)


def _confirm_wait(user):
  """updates last_confirmed for current request, returns _get_status(user)"""
>>>>>>> refactor-state
  current_row = app_tables.requests.get(user=user, current=True)
  current_row['last_confirmed'] = _now()
  if current_row['match_id']:
    matched_requests = app_tables.requests.search(match_id=current_row['match_id'], current=True)
    for row in matched_requests:
      if row['user'] != user:
        return min(row['last_confirmed'], current_row['last_confirmed'])
  return _get_status(user)


@anvil.server.callable
@anvil.tables.in_transaction
def get_status(user_id):
  user = _get_user(user_id)
  return _get_status(user)


<<<<<<< HEAD
def _get_status(user_id):
  """
  returns current_status, ref_time (or None), tallies, alt_avail
  alt_avail: Boolean, whether another match is available
    for user (if "matched") or match (if "pinged"), (else) None
  ref_time: match_start or other's last_confirmed (if "matched" and not alt_avail)
||||||| merged common ancestors
def _get_status(user_id):
  '''
  returns current_status, ref_time (or None), tallies, alt_avail
  alt_avail: Boolean, whether another match is available
    for user (if "matched") or match (if "pinged"), (else) None
  ref_time: match_start or other's last_confirmed (if "matched" and not alt_avail)
=======
def _get_status(user):
  """
  returns current_status, last_confirmed, ping_start, tallies
  last_confirmed: min of this or other's last_confirmed
  ping_start: ping_start or, for "matched", match_commence
>>>>>>> refactor-state
  assumes 2-person matches only
<<<<<<< HEAD
  """
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
  tallies = _get_tallies(user)
||||||| merged common ancestors
  '''
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
  tallies = _get_tallies(user)
=======
  """
>>>>>>> refactor-state
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
      if last_confirmed > current_row['last_confirmed']:
        status = "pinging"
        request_type = current_row['request_type']
        if request_type == "will_offer_first":
          alt_requests = [r for r in app_tables.requests.search(current=True,
                                                               match_id=None)]
        else:
          assert request_type == "receive_first"
          alt_requests = [r for r in app_tables.requests.search(current=True,
                                                               request_type="will_offer_first",
                                                               match_id=None)]
        alt_avail = len(alt_requests) > 0
        if alt_avail:
          status += "-mult"
        else:
          status += "-one"
      else:
        status = "pinged"
        request_types = [r['request_type'] for r
                         in app_tables.requests.search(match_id=current_row['match_id'],
                                                       current=True)
                         if r['user'] != user]
        assert len(request_types) == 1
        request_type = request_types[0]
        if request_type == "will_offer_first":
          alt_requests = [r for r in app_tables.requests.search(current=True,
                                                               match_id=None)]
        else:
          assert request_type == "receive_first"
          alt_requests = [r for r in app_tables.requests.search(current=True,
                                                               request_type="will_offer_first",
                                                               match_id=None)]
        alt_avail = len(alt_requests) > 0
        if alt_avail:
          status += "-mult"
        else:
          status += "-one"
    else:
      status = "requesting"
      last_confirmed = current_row['last_confirmed']
      if h.seconds_left(status, last_confirmed) <= p.CONFIRM_WAIT_SECONDS:
        status += "-confirm"
  else:
    current_matches = app_tables.matches.search(users=[user], complete=[0])
    for row in current_matches:
      i = row['users'].index(user)
      if row['complete'][i] == 0:
        status = "matched"
        ping_start = row['match_commence']
  return status, last_confirmed, ping_start, tallies


@anvil.server.callable
@anvil.tables.in_transaction
def get_tallies():
  _prune_requests()
  user = anvil.server.session['user']
  return _get_tallies(user)


def _get_tallies(user):
  tallies =	dict(receive_first=0,
                 will_offer_first=0,
                 request_em=0)
  active_users = [user]
  for row in app_tables.requests.search(current=True, match_id=None):
    if row['user'] != user:
      tallies[row['request_type']] += 1
      active_users.append(row['user'])
  assume_inactive = datetime.timedelta(days=p.ASSUME_INACTIVE_DAYS)
  cutoff_e = _now() - assume_inactive
  request_em_list = [1 for u in app_tables.users.search(enabled=True, request_em=True)
                     if u['last_login'] > cutoff_e and u not in active_users]
  tallies['request_em'] = len(request_em_list)
  return tallies


@anvil.server.callable
@anvil.tables.in_transaction
def get_code(user_id):
<<<<<<< HEAD
  """returns jitsi_code, request_type (or Nones)"""
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
||||||| merged common ancestors
  '''returns jitsi_code, request_type (or Nones)'''
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
=======
  """returns jitsi_code, request_type (or Nones)"""
  user = _get_user(user_id)
>>>>>>> refactor-state
  current_row = app_tables.requests.get(user=user, current=True)
  code = None
  request_type = None
  if current_row:
    code = current_row['jitsi_code']
    request_type = current_row['request_type']
  else:
    current_matches = app_tables.matches.search(users=[user], complete=[0])
    for row in old_matches:
      i = row['users'].index(user)
      if row['complete'][i] == 1:
        code = row['jitsi_code']
        request_type = row['request_types'][i]
  return code, request_type


<<<<<<< HEAD
@anvil.server.callable
@anvil.tables.in_transaction
def add_request(user_id, request_type):
  """
  return jitsi_code, last_confirmed (both None if no immediate match), num_emailed
  """
  #assert anvil.server.session['user_id']==user_id
  jitsi_code = None
  last_confirmed = None
  num_emailed = 0
  alt_avail = None
  if request_type=="offering":
||||||| merged common ancestors
@anvil.server.callable
@anvil.tables.in_transaction
def add_request(user_id, request_type):
  '''
  return jitsi_code, last_confirmed (both None if no immediate match), num_emailed
  '''
  #assert anvil.server.session['user_id']==user_id
  jitsi_code = None
  last_confirmed = None
  num_emailed = 0
  alt_avail = None
  if request_type=="offering":
=======
def _create_match(user, excluded=()):
  """attempt to create a match for user"""
  excluded_users = list(excluded)
  current_row = app_tables.requests.get(user=user, current=True)
  request_type = current_row['request_type']
  if request_type == "will_offer_first":
>>>>>>> refactor-state
    requests = [r for r in app_tables.requests.search(current=True,
                                                      match_id=None)
                if r['user'] not in [user] + excluded_users]
  else:
    assert request_type == "receive_first"
    requests = [r for r in app_tables.requests.search(current=True,
                                                      request_type="will_offer_first",
                                                      match_id=None)
                if r['user'] not in [user] + excluded_users]
  if requests:
    current_row['ping_start'] = _now()
    current_row['match_id'] = _new_match_id()
    current_row['jitsi_code'] = _new_jitsi_code()
    cms = [r['cancelled_matches'] for r in requests]
    eligible_requests = [r for r in requests if r['cancelled_matches'] == min(cms)]
    earliest_request = min(eligible_requests, key=lambda row: row['start'])
    earliest_request['ping_start'] = current_row['ping_start']
    earliest_request['match_id'] = current_row['match_id']
<<<<<<< HEAD
    earliest_request['jitsi_code'] = jitsi_code
    last_confirmed = earliest_request['last_confirmed']
    alt_avail = len(requests) > 1
  else:
    num_emailed = request_emails(request_type)
  return jitsi_code, last_confirmed, num_emailed, alt_avail
      
    
def _create_match(exclude_user=None):
  """attempt to create a match from existing requests"""
||||||| merged common ancestors
    earliest_request['jitsi_code'] = jitsi_code
    last_confirmed = earliest_request['last_confirmed']
    alt_avail = len(requests) > 1
  else:
    num_emailed = request_emails(request_type)
  return jitsi_code, last_confirmed, num_emailed, alt_avail
      
    
def _create_match(exclude_user=None):
  'attempt to create a match from existing requests'
=======
    earliest_request['jitsi_code'] = current_row['jitsi_code']
    lc = min(current_row['last_confirmed'],
             earliest_request['last_confirmed'])
    if (current_row['ping_start'] - lc).seconds <= p.BUFFER_SECONDS:
      _match_commenced(user)


def _create_matches(excluded=()):
  """attempt to create a match from existing requests, iterate"""
  excluded_users = list(excluded)
>>>>>>> refactor-state
  # find top request in queue
  all_requests = [r for r in app_tables.requests.search(current=True,
                                                        match_id=None)
                    if r['user'] not in excluded_users]
  if all_requests:
    all_cms = [r['cancelled_matches'] for r in all_requests]
    all_eligible_requests = [r for r in all_requests if r['cancelled_matches'] == min(all_cms)]
    current_row = min(all_eligible_requests, key=lambda row: row['start'])
    user = current_row['user']
    # attempt to create a match for top request
    _create_match(user, excluded_users)
    # attempt to create matches for remaining requests
    _create_matches(excluded_users + [user])


@anvil.server.callable
@anvil.tables.in_transaction
def add_request(user_id, request_type):
  """
  return status, last_confirmed, ping_start, num_emailed
  """
  num_emailed = 0
  user = _get_user(user_id)
  status, last_confirmed, ping_start, tallies = _get_status(user)
  assert status == None
  _add_request_row(user, request_type)
  _create_matches()
  status, last_confirmed, ping_start, tallies = _get_status(user)
  if status == "requesting":
    num_emailed = _request_emails(request_type)
  return status, last_confirmed, ping_start, num_emailed


@anvil.server.callable
@anvil.tables.in_transaction
def cancel(user_id):
  """
  Remove request and cancel match (if applicable)
<<<<<<< HEAD
  Returns None
  """
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
||||||| merged common ancestors
  Returns None
  '''
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
=======
  Returns tallies
  """
  user = _get_user(user_id)
>>>>>>> refactor-state
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
      _create_matches()
  return _get_tallies(user)

<<<<<<< HEAD
    
@anvil.server.callable
@anvil.tables.in_transaction
def cancel_match(user_id):
  """
  cancel match (if applicable)--but not remove request
  Returns updated status
  """
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
||||||| merged common ancestors
    
@anvil.server.callable
@anvil.tables.in_transaction
def cancel_match(user_id):
  '''
  cancel match (if applicable)--but not remove request
  Returns updated status
  '''
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
=======

def _cancel_match(user):
>>>>>>> refactor-state
  current_row = app_tables.requests.get(user=user, current=True)
  if current_row:
    if current_row['match_id']:
      matched_requests = app_tables.requests.search(match_id=current_row['match_id'],
                                                    current=True)
      for row in matched_requests:
        row['ping_start'] = None
        row['match_id'] = None
        row['jitsi_code'] = None
      current_row['cancelled_matched'] += 1
      if h.seconds_left("requesting", current_row['last_confirmed']) <= 0:
        current_row['current'] = False
      _create_matches([user])
      _create_match(user)
  return _get_status(user)


@anvil.server.callable
@anvil.tables.in_transaction
<<<<<<< HEAD
def cancel_other(user_id):
  """
  return new_status
  Upon failure of other to confirm match
||||||| merged common ancestors
def cancel_other(user_id):
  '''
  return new_status
  Upon failure of other to confirm match
=======
def cancel_match(user_id):
  """
>>>>>>> refactor-state
  cancel match (if applicable)--but not remove request
<<<<<<< HEAD
  """
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
||||||| merged common ancestors
  '''
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
=======
  Returns updated status
  """
  user = _get_user(user_id)
  return _cancel_match(user)


def _cancel_other(user):
>>>>>>> refactor-state
  current_row = app_tables.requests.get(user=user, current=True)
  if current_row:
    if current_row['match_id']:
      matched_requests = app_tables.requests.search(match_id=current_row['match_id'],
                                                    current=True)
      excluded_users = []
      for row in matched_requests:
        row['ping_start'] = None
        row['match_id'] = None
        row['jitsi_code'] = None
        if row['user'] != user:
          excluded_users += [row['user']]
          row['cancelled_matches'] += 1
          # row['current'] = False
      if h.seconds_left("requesting", current_row['last_confirmed']) <= 0:
        current_row['current'] = False
      _create_matches(excluded_users)
      _create_match(user)
  return _get_status(user)


@anvil.server.callable
@anvil.tables.in_transaction
def cancel_other(user_id):
  """
  return new status
  Upon failure of other to confirm match
  cancel match (if applicable)--but not remove request
  """
  user = _get_user(user_id)
  return _cancel_other(user)


@anvil.server.callable
@anvil.tables.in_transaction
def match_commenced(user_id):
<<<<<<< HEAD
  """
  return status, match_start, jitsi_code, request_type
||||||| merged common ancestors
  '''
  return status, match_start, jitsi_code, request_type
=======
  """
  Returns _get_status(user)
>>>>>>> refactor-state
  Upon first commence, copy row over and delete "matching" row.
  Should not cause error if already commenced
<<<<<<< HEAD
  """
  # return status, match_start? 
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
||||||| merged common ancestors
  '''
  # return status, match_start? 
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
=======
  """
  user = _get_user(user_id)
  return _match_commenced(user)


def _match_commenced(user):
  """
  Returns _get_status(user)
  Upon first commence, copy row over and delete "matching" row.
  Should not cause error if already commenced
  """
>>>>>>> refactor-state
  current_row = app_tables.requests.get(user=user, current=True)
  if current_row:
    if current_row['match_id']:
      matched_requests = app_tables.requests.search(match_id=current_row['match_id'],
                                                    current=True)
      match_start = _now()
      new_match = app_tables.matches.add_row(users=[],
                                             request_types=[],
                                             match_id=current_row['match_id'],
                                             jitsi_code=current_row['jitsi_code'],
                                             match_commence=match_start,
                                             complete=[])
      for row in matched_requests:
        new_match['users'] += [row['user']]
        new_match['request_types'] += [row['request_type']]
        new_match['complete'] += [0]
        row['current'] = False
  return _get_status(user)

@anvil.server.callable
@anvil.tables.in_transaction
def match_complete(user_id):
<<<<<<< HEAD
  """Switch 'complete' to true in matches table for user."""
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
||||||| merged common ancestors
  '''Switch 'complete' to true in matches table for user.'''
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
=======
  """Switch 'complete' to true in matches table for user, return tallies."""
  user = _get_user(user_id)
>>>>>>> refactor-state
  current_matches = app_tables.matches.search(users=[user], complete=[0])
  for row in current_matches:
    i = row['users'].index(user)
    temp = row['complete']
    temp[i] = 1
    row['complete'] = temp
  return _get_tallies(user)


def _add_request_row(user, request_type):
  now = _now()
  new_row = app_tables.requests.add_row(user=user,
                                        current=True,
                                        request_type=request_type,
                                        start=now,
                                        last_confirmed=now,
                                        cancelled_matches=0
                                       )
  return new_row


def _new_jitsi_code():
  num_chars = 5
  charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
  random.seed()
  rand_code = "".join([random.choice(charset) for i in range(num_chars)])
  code = "empathy_" + rand_code
  # match['jitsi_code'] = code
  return code


def _new_match_id():
  match_id = uuid.uuid4()
  return match_id.int


@anvil.server.callable
def get_user_info(user_id):
<<<<<<< HEAD
  """Return user info, initializing it for new users"""
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
||||||| merged common ancestors
  '''Return user info, initializing it for new users'''
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
=======
  """Return user info, initializing it for new users"""
  user = _get_user(user_id)
>>>>>>> refactor-state
  trust = user['trust_level']
  if trust is None:
    user.update(trust_level=0)
    assert user['request_em'] == False
    assert user['match_em'] == False
  return user['trust_level'], user['request_em'], user['match_em']


@anvil.server.callable
def set_match_em(match_em_checked):
  user = anvil.server.session['user']
  user['match_em'] = match_em_checked


@anvil.server.callable
def set_request_em(request_em_checked):
  user = anvil.server.session['user']
  user['request_em'] = request_em_checked


@anvil.server.callable
def match_email():
  user = anvil.server.session['user']
  anvil.google.mail.send(to=user['email'],
                         subject="Empathy Swap - Match available",
                         text=
'''Dear Empathy Swap user,

An empathy match has been found.

Return to https://minty-sarcastic-telephone.anvil.app now to be connected for your empathy exchange.

Thanks!
Tim

p.s. You are receiving this email because you checked the box: "Notify me by email when a match is found." To stop receiving these emails, ensure this box is unchecked when requesting empathy.
''')
<<<<<<< HEAD
  
def request_emails(request_type):
  """email all users with request_em_check_box checked who logged in recently"""
  assume_inactive = datetime.timedelta(days=p.ASSUME_INACTIVE_DAYS) 
||||||| merged common ancestors
  
def request_emails(request_type):
  '''email all users with request_em_check_box checked who logged in recently'''
  assume_inactive = datetime.timedelta(days=p.ASSUME_INACTIVE_DAYS) 
=======


def _request_emails(request_type):
  """email all users with request_em_check_box checked who logged in recently"""
  assume_inactive = datetime.timedelta(days=p.ASSUME_INACTIVE_DAYS)
>>>>>>> refactor-state
  user = anvil.server.session['user']
  if request_type == "receive_first":
    request_type_text = 'an empathy exchange with someone willing to offer empathy first.'
  else:
    assert request_type == "will_offer_first"
    request_type_text = 'an empathy exchange.'
  cutoff_e = _now() - assume_inactive
  emails = [u['email'] for u in app_tables.users.search(enabled=True, request_em=True)
                       if u['last_login'] > cutoff_e and u != user]
  for email_address in emails:
    anvil.google.mail.send(to=email_address,
                           subject="Empathy Swap - Request active",
                           text=
'''Dear Empathy Swap user,

Someone has requested ''' + request_type_text + '''

Return to https://minty-sarcastic-telephone.anvil.app now and request empathy to be connected (if you are first to do so).

Thanks!
Tim

p.s. You are receiving this email because you checked the box: "Notify me of empathy requests by email." To stop receiving these emails, return to the link above and change the setting.
''')
  return len(emails)
