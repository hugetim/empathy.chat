from anvil import *
import anvil.server
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users

class LoginForm(LoginFormTemplate):
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    
  def form_show (self, **event_args):
    # Do the code here to show this blank form.
    while not anvil.users.get_user():
      anvil.users.login_with_form()
    open_form('MatchForm')