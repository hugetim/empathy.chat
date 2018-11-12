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
  timeout = datetime.timedelta(minutes=30) 
  assume_complete = datetime.timedelta(hours=4) 
  initialize_session(user_id)
  user = anvil.server.session['user']
  # Prune unmatched requests, including from this user
  cutoff_r = datetime.datetime.utcnow() - timeout
  old_requests = (r for r in app_tables.requests.search(current=True, match_id=None)
                    if r['last_confirmed'] > cutoff_r)
  for row in old_requests:
    row['current'] = False
  # Complete old matches for this user
  cutoff_m = datetime.datetime.utcnow() - assume_complete
  old_matches = (m for m in app_tables.matches.search(users=[user], complete=[0])
                   if m['match_commence'] > cutoff)
  for row in old_matches:
    i = row['users'].index(user)
    row['complete'][i] = 1
  # Return after confirming wait
  trust_level = get_trust_level(user_id) 
  current_status, match_start = get_status_private(user_id)
  if current_status in ('requesting', 'offering'):
    confirm_wait_private(user_id)
  return trust_level, current_status, match_start

def initialize_session(user_id):
  '''initialize session state: user_id, user, and current_row'''
  anvil.server.session['user_id'] = user_id
  user = app_tables.users.get_by_id(user_id)
  anvil.server.session['user'] = user
  current_row = app_tables.requests.get(user=user, current=True)
  anvil.server.session['current_row'] = current_row

@anvil.server.callable
@anvil.tables.in_transaction
def confirm_wait(user_id):
  confirm_wait_private(user_id)
  
def confirm_wait_private(user_id):
  '''updates last_confirmed for current (unmatched) request'''
  user = app_tables.users.get_by_id(user_id)
  current_row = anvil.server.session['current_row']
  assert current_row['match_id']==None
  current_row['last_confirmed'] = datetime.datetime.utcnow()

@anvil.server.callable
@anvil.tables.in_transaction
def get_status(user_id):
  return get_status_private(user_id)

def get_status_private(user_id):
  '''
  returns current_status, match_start (or None)
  assumes 2-person matches only
  '''
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
  current_row = anvil.server.session['current_row']
  status = None
  match_start = None
  if current_row and current_row['current']==True: #uses short-circuiting to avoid error
    if current_row['match_id']:
      matched_request_starts = (r['start'] for r
                                in app_tables.requests.search(match_id=current_row['match_id']))
      match_start = matched_request_starts.max()
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
  '''returns jitsi_code or None'''
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
  current_row = anvil.server.session['current_row']
  code = None
  if current_row:
    code = current_row['jitsi_code']
  else:
    current_matches = app_tables.matches.search(users=[user], complete=[0])
    for row in old_matches:
      i = row['users'].index(user)
      if row['complete'][i]==True:
        code = row['jitsi_code']
  return code

@anvil.server.callable
@anvil.tables.in_transaction
def add_request(user_id, request_type):
  '''
  return jitsi_code, last_confirmed (None if)
  '''
  jitsi_code = None
  last_confirmed = None
  if request_type=="offering":
    requests = app_tables.requests.search(current=True,
                                          match_id=None)
  else: 
    assert request_type=="requesting"
    requests = app_tables.requests.search(current=True,
                                          request_type="offering",
                                          match_id=None)    
  # if no match, add new row, else add request info
  current_row = add_request_row(user_id, request_type)
  anvil.server.session['current_row'] = current_row
  if requests:
    jitsi_code = new_jitsi_code()
    current_row['match_id'] = new_match_id()
    current_row['jitsi_code'] = jitsi_code
    earliest_request = requests.min(key=lambda row : row['start'])
    earliest_request['match_id'] = current_row['match_id']
    earliest_request['jitsi_code'] = jitsi_code
    last_confirmed = earliest_request['last_confirmed']
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
  current_row = anvil.server.session['current_row']
  status = None
  match_start = None
  if current_row and current_row['current']==True: #uses short-circuiting to avoid error
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
  Upon failure of other to confirm match
  Remove request and cancel match (if applicable)
  Returns None
  '''
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
  current_row = anvil.server.session['current_row']
  status = None
  match_start = None
  if current_row and current_row['current']==True: #uses short-circuiting to avoid error
    if current_row['match_id']:
      matched_requests = app_tables.requests.search(match_id=current_row['match_id'])
      for row in matched_requests:
        row['match_id'] = None
        row['jitsi_code'] = None
        if row['user'] != user:
          row['current'] = False
        
@anvil.server.callable
@anvil.tables.in_transaction
def match_commenced(user_id):
  '''
  Upon first commence, copy row over and delete "matching" row.
  Should not cause error if already commenced
  '''
  # return status, match_start? 
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
  current_row = anvil.server.session['current_row']
  status = None
  match_start = None
  if current_row and current_row['current']==True: #uses short-circuiting to avoid error
    if current_row['match_id']:
      matched_requests = app_tables.requests.search(match_id=current_row['match_id'])
      match_start = datetime.datetime.utcnow()
      new_match = app_tables.matches.add_row(users=[],
                                             match_id=current_row['match_id'],
                                             jitsi_code=current_row['jitsi_code'],
                                             match_commence=match_start,
                                             complete=[])
      for row in matched_requests:
        new_match['users'].append(row['user'])
        new_match['complete'].append(0)
      status = "empathy"
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
def match_complete(user_id):
  '''Switch 'complete' to true in matches table for user.'''
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
  current_matches = app_tables.matches.search(users=[user], complete=[0])
  for row in current_matches:
    i = row['users'].index(user)
    row['complete'][i] = 1
  
def add_request_row(user_id, request_type):
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
  now = datetime.datetime.utcnow()
  new_row = app_tables.requests.add_row(user=user,
                                        current=True,
                                        request_type=request_type,
                                        start_time=now,
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
def get_trust_level(user_id):
  assert anvil.server.session['user_id']==user_id
  user = anvil.server.session['user']
  trust = user['trust_level']
  if trust == None:
    user.update(trust_level=0)
  return user['trust_level']