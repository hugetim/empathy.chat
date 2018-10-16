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
def add_request(user_id):
    if app_tables.matching.get() == None:
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
        earliest_offer['request_time'] = datetime.datetime.now()
        return create_jitsi(earliest_offer)

@anvil.server.callable
def add_offer(user_id):
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
        earliest_request['offer_time'] = datetime.datetime.now()
        return create_jitsi(earliest_request)

@anvil.server.callable
def get_status(user_id):
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
def cancel(user_id):
  match_r = app_tables.matching.get(request_id=user_id)
  if match_r != None:
    match_r['request_id'] = None
    match_r['request_time'] = None
    match_r['jitsi_code'] = None
  else:
    match_o = app_tables.matching.get(offer_id=user_id)
    if match_o != None:
      match_o['offer_id'] = None
      match_o['offer_time'] = None
      match_o['jitsi_code'] = None
    
      
      
def add_request_row(user_id):
  new_row = app_tables.matching.add_row(request_id=anvil.users.get_user().get_id(), 
                                        request_time=datetime.datetime.now())
  return new_row

def add_offer_row(user_id):
  new_row = app_tables.matching.add_row(offer_id=anvil.users.get_user().get_id(), 
                                        offer_time=datetime.datetime.now())
  return new_row

def create_jitsi(match):
  numchars = 7
  charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
  random.seed()
  randcode = "".join([random.choice(charset) for i in range(numchars)])
  code = "empathy" + randcode
  match['jitsi_code'] = code
  return code

def complete(user_id):
  match = app_tables.matching.get(request_id=user_id)
  if match == None:
    match = app_tables.matching.get(offer_id=user_id)
  app_tables.matches.add_row(request_id=match['request_id'],
                             request_time=match['request_time'],
                             offer_id=match['offer_id'],
                             offer_time=match['offer_time'],
                             jitsi_code=code)
  match.delete()

@anvil.server.callable
def get_trust_level(user_id):
  user = app_tables.users.get_by_id(user_id)
  return user['trust_level']