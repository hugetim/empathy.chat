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
def prune_requests(user_id):
  '''
  Assumed to run upon initializing Form1
  returns trust_level, current_status, match_start (or None)
  prunes old requests/offers
  updates last_confirmed if currently requesting/offering
  '''
  timeout = datetime.timedelta(minutes=30) 
  assume_complete = datetime.timedelta(hours=4) 
  # Prune unmatched requests, including from this user
  cutoff_r = datetime.datetime.utcnow() - timeout
  old_requests = (r for r in app_tables.requests.search(current=True, match_id=None)
                    if r['last_confirmed'] > cutoff_r)
  for row in old_requests:
    row['current'] = False
  # Complete old matches for this user
  cutoff_m = datetime.datetime.utcnow() - assume_complete
  old_matches = (m for m in app_tables.matches.search(users=user, complete=False)
                   if m['match_commence'] > cutoff)
  for row in old_matches:
    i = row['users'].index(user)
    row['complete'][i] = True
  # Return after confirming wait
  trust_level = get_trust_level(user_id)
  initialize_session(user_id)
  current_status, match_start = get_status(user_id)
  if current_status in ('requesting', 'offering'):
    confirm_wait(user_id)
  return trust_level, current_status, match_start

@anvil.tables.in_transaction
def initialize_session(user_id):
  '''initialize session state: user_id, user, and current_row'''
  anvil.server.session('user_id') = user_id
  user = app_tables.users.get_by_id(user_id)
  anvil.server.session('user') = user
  current_row = app_tables.requests.get(user=user, current=True)
  anvil.server.session('current_row') = current_row

@anvil.server.callable
@anvil.tables.in_transaction
def confirm_wait(user_id):
  '''updates last_confirmed for current (unmatched) request'''
  user = app_tables.users.get_by_id(user_id)
  current_row = app_tables.requests.get(user=user, current=True)
  assert current_row['match_id']==None
  current_row['last_confirmed'] = datetime.datetime.utcnow()

@anvil.server.callable
@anvil.tables.in_transaction
def get_status(user_id):
  '''
  returns current_status, match_start (or None)
  assumes 2-person matches only
  '''
  assert anvil.server.session('user_id')==user_id
  user = anvil.server.session('user')
  current_row = anvil.server.session('current_row')
  status = None
  match_start = None
  if current_row and current_row['current']==True: #uses short-circuiting to avoid error
    if current_row['match_id']:
      matched_request_starts = (r['start'] for r
                                in app_tables.requests.search(match_id=current_row['match_id'],
                                                              tables.order_by('start', ascending=False)))
      match_start = matched_request_starts[0]
      if match_start==current_row['start']:
        status = "matched"
      else:
        status = "pinged"
    else:
      status = current_row['request_type']
  else:
    current_matches = app_tables.matches.search(users=user, complete=False)
    for row in current_matches:
      i = row['users'].index(user)
      if row['complete'][i]==True:
        status = "empathy"
        match_start = row['match_commence']
  return status, match_start

@anvil.server.callable
@anvil.tables.in_transaction
def get_code(user_id):
  '''returns jitsi_code or None'''
  assert anvil.server.session('user_id')==user_id
  user = anvil.server.session('user')
  current_row = anvil.server.session('current_row')
  code = None
  if current_row:
    code = current_row['jitsi_code']
  else:
    current_matches = app_tables.matches.search(users=user, complete=False)
    for row in old_matches:
      i = row['users'].index(user)
      if row['complete'][i]==True:
        code = row['jitsi_code']
  return code

@anvil.server.callable
@anvil.tables.in_transaction
def add_request(user_id, request_type):
  zaphod_row = (app_tables.people.get(name="Zaphod Beeblebrox")
               or app_tables.people.add_row(name="Zaphod Beeblebrox", age=42))
    if app_tables.matching.get() == None: #empty table
      add_request_row(user_id)
    else:
      offers = [row for row in app_tables.matching.search()
            if row["offer_id"] != None and row["request_id"] == None]
      # if no offers, add new row, else add request info
      if not offers:
        add_request_row(user_id)
      else:
        offers.sort(key = lambda row: row['offer_time'])
        earliest_offer = offers[0]
        earliest_offer['request_id'] = user_id
        earliest_offer['request_time'] = datetime.datetime.utcnow()
        return create_jitsi(earliest_offer)
# add_offer(user_id):
    if app_tables.matching.get() == None:
      add_offer_row(user_id)
    else:
      requests = [row for row in app_tables.matching.search()
            if row["request_id"] != None and row["offer_id"] == None]
      # if no offers, add new row, else add request info
      if not requests:
        add_offer_row(user_id)
      else:
        requests.sort(key = lambda row: row['request_time'])
        earliest_request = requests[0]
        earliest_request['offer_id'] = user_id
        earliest_request['offer_time'] = datetime.datetime.utcnow()
        return create_jitsi(earliest_request)

@anvil.server.callable
@anvil.tables.in_transaction
def cancel(user_id):


@anvil.server.callable
@anvil.tables.in_transaction
def cancel_other(user_id):
  '''Upon failure of other to confirm match'''
  
        
@anvil.server.callable
@anvil.tables.in_transaction
def match_commenced(user_id):
  '''
  Upon first commence, copy row over and delete "matching" row.
  Should not cause error if already commenced
  '''
  # return status, match_start? 
  assert anvil.server.session('user_id')==user_id
  user = anvil.server.session('user')
  current_row = anvil.server.session('current_row')
  status = None
  match_start = None
  if current_row and current_row['current']==True: #uses short-circuiting to avoid error
    if current_row['match_id']:
      matched_requests = (r for r
                            in app_tables.requests.search(match_id=current_row['match_id'],
                                                          tables.order_by('start', ascending=True)))
      match_start = datetime.datetime.utcnow()
      new_match = app_tables.matches.add_row(users=[],
                                             match_id=current_row['match_id'],
                                             jitsi_code=current_row['jitsi_code'],
                                             match_commence=match_start,
                                             complete=[])
      for row in matched_requests:
        new_match['users'].append(row['user'])
        new_match['complete'].append(False)
      status = "empathy"
      ########################################################################################restart here
    else:
      status = current_row['request_type']
  else:
    current_matches = app_tables.matches.search(users=user, complete=False)
    for row in current_matches:
      i = row['users'].index(user)
      if row['complete'][i]==True:
        status = "empathy"
        match_start = row['match_commence']
  return status, match_start

@anvil.server.callable
@anvil.tables.in_transaction
def match_complete(user_id):
  '''Switch 'complete' to true in matches table for user.'''
  assert anvil.server.session('user_id')==user_id
  user = anvil.server.session('user')
  current_matches = app_tables.matches.search(users=user, complete=False)
  for row in current_matches:
    i = row['users'].index(user)
    row['complete'][i] = True
  
def add_request_row(user_id, request_type):
  assert anvil.server.session('user_id')==user_id
  user = anvil.server.session('user')
  now = datetime.datetime.utcnow()
  new_row = app_tables.requests.add_row(user=user,
                                        current=True,
                                        request_type=request_type,
                                        start_time=now,
                                        last_confirmed=now)
  return new_row

def create_jitsi():
  numchars = 5
  charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
  random.seed()
  randcode = "".join([random.choice(charset) for i in range(numchars)])
  code = "empathy_" + randcode
  #match['jitsi_code'] = code
  return code

def create_match_id():
  match_id = uuid.uuid4()
  return match_id.int

@anvil.server.callable
def get_trust_level(user_id):
  assert anvil.server.session('user_id')==user_id
  user = anvil.server.session('user')
  trust = user['trust_level']
  if trust == None:
    user.update(trust_level=0)
  return user['trust_level']