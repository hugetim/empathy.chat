from ._anvil_designer import SignupTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class Signup(SignupTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.

  def email_box_pressed_enter(self, **event_args):
    """This method is called when the user presses Enter in this text box"""
    self.raise_event('x-close-alert', value="email")

  def google_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.new_user = anvil.users.signup_with_google()
    #self.raise_event('x-close-alert', value="google")


