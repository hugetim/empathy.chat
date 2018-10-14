from anvil import *
import anvil.server
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.users

class Form1(Form1Template):
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    while not anvil.users.login_with_form():
      pass

  def request_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if app_tables.offers.get() == None:
      new_row = app_tables.requests.add_row(name=anvil.users.get_user().get_id(), start_time=datetime.datetime.now())
      self.status.text = "Status: Requesting empathy. Awaiting an offer..."
    else:
      oldest_offer = list(app_tables.offers.search(tables.order_by("start_time", ascending=True))[:1])
      self.make_match(anvil.users.get_user().get_id(),oldest_offer[0]['name'])
      
  def make_match(self,requester, offerer):
    self.status.text = "Making match with " + requester + " and " + offerer




