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
    if app_tables.matches.get() == None:
      add_request_row(user_id)
    else:
      offers = [row for row in app_tables.matches.search()
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
    if app_tables.matches.get() == None:
      add_offer_row(user_id)
    else:
      requests = [row for row in app_tables.matches.search()
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

def add_request_row(user_id):
  new_row = app_tables.matches.add_row(request_id=anvil.users.get_user().get_id(), request_time=datetime.datetime.now())
  return new_row

def add_offer_row(user_id):
  new_row = app_tables.matches.add_row(offer_id=anvil.users.get_user().get_id(), offer_time=datetime.datetime.now())
  return new_row

def create_jitsi(match):
  random.seed()
  randint = random.randint(1,1000000000)
  code = "empathy" + str(randint)
  match['jitsi_code'] = code
  return code
  