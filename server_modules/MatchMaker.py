import anvil.tables as tables
from anvil.tables import app_tables
import anvil.users
import anvil.server

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
      new_row = app_tables.matches.add_row(request_id=anvil.users.get_user().get_id())
    else:
      #make match or add a new request row
      pass
      #top_row = list(app_tables.offers.search(tables.order_by("start_time", ascending=True))[:1])[0]
      #self.make_match(anvil.users.get_user().get_id(),oldest_offer[0]['name'])