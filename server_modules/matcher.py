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
  timeout = datetime.timedelta(seconds=2*p.CONFIRM_WAIT_SECONDS)
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
  email_in_list = None
  if trust_level==0:
    email_in_list = _email_in_list(user['email'])
    if email_in_list:
      trust_level = 1
      user['trust_level'] = trust_level
    else:
      user['enabled'] = False
  current_status, match_start, tallies = _get_status(user_id)
  if current_status in ('requesting', 'offering'):
    _confirm_wait(user_id)
  return trust_level, request_em, match_em, current_status, match_start, tallies, email_in_list


def _initialize_session(user_id):
  '''initialize session state: user_id, user, and current_row'''
  anvil.server.session['user_id'] = user_id
  user = app_tables.users.get_by_id(user_id)
  anvil.server.session['user'] = user

  
def _email_in_list(email):
  sheet = app_files._2018_integration_program['Sheet1']
  for row in sheet.rows:
    if _emails_equal(email, row['email']):
      return True
  return False
      
def _emails_equal(a, b):
  emre = re.compile(r"^([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)$")
  amatch = emre.search(a)
  bmatch = emre.search(b)
  return amatch.group(1)==bmatch.group(1) and amatch.group(2).lower()==bmatch.group(2).lower()

  
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
  returns current_status, match_start (or None), tallies
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
  tallies =	{
    "requesting": 0,
    "offering": 0,
    "request_em": 0
  }
  tallies = _get_tallies(user)
  return status, match_start, tallies

@anvil.server.callable
@anvil.tables.in_transaction
def get_tallies():
  user = anvil.server.session['user']
  return _get_tallies(user)


def _get_tallies(user):
  active_users = [user]
  for row in app_tables.requests.search(current=True, match_id=None):
    if row['user']!=user:
      tallies[row['request_type']] += 1
      active_users.append(row['user'])
  assume_inactive = datetime.timedelta(days=p.ASSUME_INACTIVE_DAYS) 
  cutoff_e = datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc()) - assume_inactive
  request_em_list = [1 for u in app_tables.users.search(enabled=True, request_em=True)
                      if u['last_login'] > cutoff_e and u not in active_users]
  tallies['request_em'] = len(request_em_list)
  
  
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
  return jitsi_code, last_confirmed (both None if no immediate match), num_emailed
  '''
  assert anvil.server.session['user_id']==user_id
  jitsi_code = None
  last_confirmed = None
  num_emailed = 0
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
    num_emailed = request_emails(request_type)
  return jitsi_code, last_confirmed, num_emailed


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
  anvil.google.mail.send(to = user['email'],
                         subject = "Empathy Swap - Match available",
                         text = 
'''Dear Empathy Swap user,
    
An empathy match has been found. 
                                                      
Return to https://minty-sarcastic-telephone.anvil.app now to be connected for your empathy exchange.
                           
Thanks!
Tim

p.s. You are receiving this email because you checked the box: "Notify me by email when a match is found." To stop receiving these emails, ensure this box is unchecked when requesting empathy.
''')
  
def request_emails(request_type):
  '''email all users with request_em_check_box checked who logged in recently'''
  assume_inactive = datetime.timedelta(days=p.ASSUME_INACTIVE_DAYS) 
  user = anvil.server.session['user']
  if request_type=="requesting":
    request_type_text = 'an empathy exchange with someone willing to offer empathy first.'
  else:
    assert request_type=="offering"
    request_type_text = 'an empathy exchange.'
  cutoff_e = datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc()) - assume_inactive
  emails = [u['email'] for u in app_tables.users.search(enabled=True, request_em=True)
                       if u['last_login'] > cutoff_e and u!=user]
  for email_address in emails:
    anvil.google.mail.send(to = email_address,
                           subject = "Empathy Swap - Request active",
                           text = 
'''Dear Empathy Swap user,
    
Someone has requested ''' + request_type_text + '''
                                                      
Return to https://minty-sarcastic-telephone.anvil.app now and request empathy to be connected (if you are first to do so).
                           
Thanks!
Tim

p.s. You are receiving this email because you checked the box: "Notify me of empathy requests by email." To stop receiving these emails, return to the link above and change the setting.
''')                      
  return len(emails)