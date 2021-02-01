from ._anvil_designer import LoginFormTemplate
from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.users
from .. import rosenberg
from datetime import date


class LoginForm(LoginFormTemplate):
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.quote_label.text = rosenberg.quote_of_the_day(date.today())
    
  def form_show (self, **event_args):
    # Do the code here to show this blank form.
    while not anvil.users.get_user():
      anvil.users.login_with_form()
    self.card_1.visible = True
    self.init_dict = anvil.server.call('init')
    self.enter_button.visible = True

  def enter_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    open_form('MenuForm', item=self.init_dict)

