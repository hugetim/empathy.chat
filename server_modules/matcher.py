import anvil.email
import anvil.google.auth, anvil.google.drive, anvil.google.mail
from anvil.google.drive import app_files
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.users
import anvil.server
import random
import datetime
import uuid
import anvil.tz

# This is a server module. It runs on the Anvil server,
# rather than in the user's browser.
#
# To allow anvil.server.call() to call functions here, we mark
# them with @anvil.server.callable.
# Here is an example - you can replace it with your own:
#
# @anvil.server.callable
# def say_hello(name):
#   print("Hello, " + name + "!")
#   return 42
#

@anvil.server.callable
@anvil.tables.in_transaction
def prune(user_id):
  '''
  Assumed to run upon initializing Form1
  returns trust_level, current_status, match_start (or None)
  prunes old requests/offers
  updates last_confirmed if currently requesting/offering
  '''
  timeout = datetime.timedelta(minutes=30) # should be double Form1.confirm_wait_seconds
  assume_complete = datetime.timedelta(hours=4) 
  _initialize_session(user_id)
  user = anvil.server.session['user']
  # Prune unmatched requests, including from this user
  cutoff_r = datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc()) - timeout
  old_requests = (r for r in app_tables.requests.search(current=True, match_id=None)
                    if r['last_confirmed'] < cutoff_r)
  for row in old_requests:
    row['current'] = False
  # Complete old matches for this user
  cutoff_m = datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc()) - assume_complete
  old_matches = (m for m in app_tables.matches.search(users=[user], complete=[0])
                   if m['match_commence'] < cutoff_m)
  for row in old_matches:
    i = row['users'].index(user)
    temp = row['complete']
    temp[i] = 1
    row['complete'] = temp
  # Return after confirming wait
  trust_level, request_em, match_em = get_user_info(user_id) 
  current_status, match_start = _get_status(user_id)
  if current_status in ('requesting', 'offering'):
    _confirm_wait(user_id)
  return trust_level, request_em, match_em, current_status, match_start


def _initialize_session(user_id):
  '''initialize session state: user_id, user, and current_row'''
  anvil.server.session['user_id'] = user_id
  user = app_tables.users.get_by_id(user_id)
  anvil.server.session['user'] = user

  
@anvil.server.callable
@anvil.tables.in_transaction
def confirm_wait(user_id):
  _confirm_wait(user_id)
  
  
def _confirm_wait(user_id):
  '''updates last_confirmed for current (unmatched) request'''
  user = app_tables.users.get_by_id(user_id)
  current_row = app_tables.requests.get(user=user, current=True)
  assert current_row['match_id']==None
  current_row['last_confirmed'] = datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc())

  
@anvil.server.callable
@anvil.tables.in_transaction
def get_status(user_id):
  return _get_status(user_id)


def _get_status(user_id):
  '''
  returns current_status, match_start (or None)
  assumes 2-person matches only
  '''
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
  current_row = app_tables.requests.get(user=user, current=True)
  status = None
  match_start = None
  if current_row:
    if current_row['match_id']:
      matched_request_starts = [r['start'] for r
                                in app_tables.requests.search(match_id=current_row['match_id'])]
      match_start = max(matched_request_starts)
      if match_start==current_row['start']:
        status = "matched"
      else:
        status = "pinged"
    else:
      status = current_row['request_type']
  else:
    current_matches = app_tables.matches.search(users=[user], complete=[0])
    for row in current_matches:
      i = row['users'].index(user)
      if row['complete'][i]==0:
        status = "empathy"
        match_start = row['match_commence']
  return status, match_start


@anvil.server.callable
@anvil.tables.in_transaction
def get_code(user_id):
  '''returns jitsi_code, request_type (or Nones)'''
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
  current_row = app_tables.requests.get(user=user, current=True)
  code = None
  if current_row:
    code = current_row['jitsi_code']
    request_type = current_row['request_type']
  else:
    current_matches = app_tables.matches.search(users=[user], complete=[0])
    for row in old_matches:
      i = row['users'].index(user)
      if row['complete'][i]==True:
        code = row['jitsi_code']
        request_type = row['request_types'][i]
  return code, request_type


@anvil.server.callable
@anvil.tables.in_transaction
def add_request(user_id, request_type):
  '''
  return jitsi_code, last_confirmed (both None if no immediate match)
  '''
  assert anvil.server.session['user_id']==user_id
  jitsi_code = None
  last_confirmed = None
  if request_type=="offering":
    requests = [r for r in app_tables.requests.search(current=True,
                                                      match_id=None)]
  else: 
    assert request_type=="requesting"
    requests = [r for r in app_tables.requests.search(current=True,
                                                      request_type="offering",
                                                      match_id=None)]    
  current_row = add_request_row(user_id, request_type)
  if requests:
    jitsi_code = new_jitsi_code()
    current_row['match_id'] = new_match_id()
    current_row['jitsi_code'] = jitsi_code
    earliest_request = min(requests, key=lambda row: row['start'])
    earliest_request['match_id'] = current_row['match_id']
    earliest_request['jitsi_code'] = jitsi_code
    last_confirmed = earliest_request['last_confirmed']
  else:
    request_emails(request_type)
  return jitsi_code, last_confirmed


@anvil.server.callable
@anvil.tables.in_transaction
def cancel(user_id):
  '''
  Remove request and cancel match (if applicable)
  Returns None
  '''
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
  current_row = app_tables.requests.get(user=user, current=True)
  if current_row:
    if current_row['match_id']:
      matched_requests = app_tables.requests.search(match_id=current_row['match_id'])
      for row in matched_requests:
        row['match_id'] = None
        row['jitsi_code'] = None
    current_row['current'] = False

    
@anvil.server.callable
@anvil.tables.in_transaction
def cancel_other(user_id):
  '''
  return new_status
  Upon failure of other to confirm match
  Remove request and cancel match (if applicable)
  '''
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
  current_row = app_tables.requests.get(user=user, current=True)
  if current_row:
    if current_row['match_id']:
      matched_requests = app_tables.requests.search(match_id=current_row['match_id'])
      for row in matched_requests:
        row['match_id'] = None
        row['jitsi_code'] = None
        if row['user'] != user:
          row['current'] = False
      return current_row['request_type']

    
@anvil.server.callable
@anvil.tables.in_transaction
def match_commenced(user_id):
  '''
  return status, match_start, jitsi_code, request_type
  Upon first commence, copy row over and delete "matching" row.
  Should not cause error if already commenced
  '''
  # return status, match_start? 
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
  current_row = app_tables.requests.get(user=user, current=True)
  status = None
  match_start = None
  jitsi_code = None
  request_type = None
  if current_row:
    request_type = current_row['request_type']
    if current_row['match_id']:
      matched_requests = app_tables.requests.search(match_id=current_row['match_id'])
      match_start = datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc())
      jitsi_code = current_row['jitsi_code']
      new_match = app_tables.matches.add_row(users=[],
                                             request_types=[],
                                             match_id=current_row['match_id'],
                                             jitsi_code=jitsi_code,
                                             match_commence=match_start,
                                             complete=[])
      for row in matched_requests:
        new_match['users'] += [row['user']]
        new_match['request_types'] += [row['request_type']]
        new_match['complete'] += [0]
        row['current'] = False
      status = "empathy"
    else:
      status = request_type
  else:
    current_matches = app_tables.matches.search(users=[user], complete=[0])
    for row in current_matches:
      i = row['users'].index(user)
      if row['complete'][i]==0:
        status = "empathy"
        match_start = row['match_commence']
        jitsi_code = row['jitsi_code']
        request_type = row['request_types'][i]
  return status, match_start, jitsi_code, request_type


@anvil.server.callable
@anvil.tables.in_transaction
def match_complete(user_id):
  '''Switch 'complete' to true in matches table for user.'''
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
  current_matches = app_tables.matches.search(users=[user], complete=[0])
  for row in current_matches:
    i = row['users'].index(user)
    temp = row['complete']
    temp[i] = 1
    row['complete'] = temp

    
def add_request_row(user_id, request_type):
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
  now = datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc())
  new_row = app_tables.requests.add_row(user=user,
                                        current=True,
                                        request_type=request_type,
                                        start=now,
                                        last_confirmed=now)
  return new_row


def new_jitsi_code():
  numchars = 5
  charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
  random.seed()
  randcode = "".join([random.choice(charset) for i in range(numchars)])
  code = "empathy_" + randcode
  #match['jitsi_code'] = code
  return code


def new_match_id():
  match_id = uuid.uuid4()
  return match_id.int


@anvil.server.callable
def get_user_info(user_id):
  '''Return user info, initializing it for new users'''
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
  trust = user['trust_level']
  if trust == None:
    user.update(trust_level=0)
    assert user['request_em']==False
    assert user['match_em']==False
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
  google.mail.send(to = user['email'],
                   subject = "Empathy match available",
                   text = 'This is the email notification '
                        + 'you requested by checking the box: '
                        + '"Notify me by email when a match is found." '
                        + 'Return to http://tinyurl.com/nvcempathy (which '
                        + 'redirects to https://minty-sarcastic-telephone.anvil.app)'
                        + 'now to be connected for your empathy exchange.')
  
def request_emails():
  