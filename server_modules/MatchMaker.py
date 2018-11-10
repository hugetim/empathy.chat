import anvil.email
import anvil.google.auth, anvil.google.drive, anvil.google.mail
from anvil.google.drive import app_files
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.users
import anvil.server
import random
import datetime

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
  timeout = datetime.timedelta(seconds=60*30)
  # Prune unmatched requests, including from this user
  cutoff = datetime.datetime.utcnow() - timeout
  old_requests = (r for r in app_tables.requests.search(current=True, match_id=None)
                    if r['last_confirmed'] > cutoff)
  for row in old_requests:
    row['current'] = False
  # Return after confirming wait
  trust_level = get_trust_level(user_id)
  current_status, match_start = get_status(user_id)
  if current_status in ('requesting', 'offering'):
    confirm_wait(user_id)
  return trust_level, current_status, match_start

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
def get_code(user_id):
  match_r = app_tables.matching.get(request_id=user_id)
  if match_r == None:
    match_o = app_tables.matching.get(offer_id=user_id)
    if match_o != None:
      return match_o['jitsi_code']
  else:
    return match_r['jitsi_code']
  
@anvil.server.callable
@anvil.tables.in_transaction
def get_status(user_id):
  '''
  returns current_status, match_start (or None)
  '''
  match_r = app_tables.matching.get(request_id=user_id)
  if match_r == None:
    match_o = app_tables.matching.get(offer_id=user_id)
    if match_o == None:
      return None
    elif match_o['request_id'] == None:
        return "offering"
    else:
      return "matched"
  elif match_r['offer_id'] == None:
    return "requesting"
  else:
    return "matched"

@anvil.server.callable
@anvil.tables.in_transaction
def get_match_start(user_id):
  match_r = app_tables.matching.get(request_id=user_id)
  if match_r == None:
    match_o = app_tables.matching.get(offer_id=user_id)
    if match_o == None:
      return None
    else:
      return max(match_o['request_time'], match_o['offer_time'])
  else:
    return max(match_r['request_time'], match_r['offer_time']) 
      
@anvil.server.callable
@anvil.tables.in_transaction
def cancel(user_id):
  match_r = app_tables.matching.get(request_id=user_id)
  if match_r != None:
    match_r['request_id'] = None
    match_r['request_time'] = None
    match_r['jitsi_code'] = None
    if match_r['offer_id'] == None:
      match_r.delete()
  else:
    match_o = app_tables.matching.get(offer_id=user_id)
    if match_o != None:
      match_o['offer_id'] = None
      match_o['offer_time'] = None
      match_o['jitsi_code'] = None
      if match_o['request_id'] == None:
        match_o.delete()

@anvil.server.callable
@anvil.tables.in_transaction
def cancel_other(user_id):
  '''Upon failure of other to confirm match'''
  match_r = app_tables.matching.get(request_id=user_id)
  if match_r != None:
    match_r['offer_id'] = None
    match_r['offer_time'] = None
    match_r['jitsi_code'] = None
  else:
    match_o = app_tables.matching.get(offer_id=user_id)
    if match_o != None:
      match_o['request_id'] = None
      match_o['request_time'] = None
      match_o['jitsi_code'] = None      
        
@anvil.server.callable
@anvil.tables.in_transaction
def match_commenced(user_id):
  '''Upon first commence, copy row over and delete "matching" row.'''
  match_r = app_tables.matching.get(request_id=user_id)
  if match_r == None:
    match_o = app_tables.matching.get(offer_id=user_id)
    if match_o == None:
      return None
    elif match_o['request_id'] == None:
      return "offering"
    else:
      matches = app_tables.matches.get(jitsi_code=match_o['jitsi_code'])
      if matches == None:
        copy_to_matches(match_o)
      return "empathy"
  elif match_r['offer_id'] == None:
    return "requesting"
  else:
    matches = app_tables.matches.get(jitsi_code=match_r['jitsi_code'])
    if matches == None:
      copy_to_matches(match_r)
    return "empathy"      

@anvil.server.callable
@anvil.tables.in_transaction
def match_complete(user_id):
  '''Set appropriate complete time in matches table.'''
  #match_r = app_tables.matching.get(request_id=user_id)
  #if match_r == None:
  #  match_o = app_tables.matching.get(offer_id=user_id)
  #  if match_o == None:
  #    # outcome for second complete, from other user in the match
  #    pass
  #  else:
  #    assert match_o['request_id'] != None
  #    matches = app_tables.matches.get(jitsi_code=match_o['jitsi_code'])
  #    assert matches != None
  #    match_o.delete()
  #else:
  #  assert match_r['offer_id'] != None
  #  matches = app_tables.matches.get(jitsi_code=match_r['jitsi_code'])
  #  assert matches != None
  #  match_r.delete()
  #return None
  
def copy_to_matches(matching): 
  matched = app_tables.matches.add_row(request_id = matching['request_id'],
                                       request_time = matching['request_time'],
                                       offer_id = matching['offer_id'],
                                       offer_time = matching['offer_time'],
                                       jitsi_code = matching['jitsi_code'],
                                       start_time = datetime.datetime.utcnow())
  
def add_request_row(user_id):
  new_row = app_tables.matching.add_row(request_id=anvil.users.get_user().get_id(), 
                                        request_time=datetime.datetime.utcnow())
  return new_row

def add_offer_row(user_id):
  new_row = app_tables.matching.add_row(offer_id=anvil.users.get_user().get_id(), 
                                        offer_time=datetime.datetime.utcnow())
  return new_row

def create_jitsi(match):
  numchars = 7
  charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
  random.seed()
  randcode = "".join([random.choice(charset) for i in range(numchars)])
  code = "empathy_" + randcode
  match['jitsi_code'] = code
  return code

@anvil.server.callable
def get_trust_level(user_id):
  user = app_tables.users.get_by_id(user_id)
  trust = user['trust_level']
  if trust == None:
    user.update(trust_level=0)
  return user['trust_level']