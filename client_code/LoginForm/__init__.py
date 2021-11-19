from ._anvil_designer import LoginFormTemplate
from anvil import *
import anvil.users
import anvil.server
from .. import rosenberg
from datetime import date
from .. import parameters
from ..MenuForm.MatchForm import MatchForm
from .. import glob


class LoginForm(LoginFormTemplate):
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.quote_label.text = rosenberg.quote_of_the_day(date.today())
    
  def form_show(self, **event_args):
    # Do the code here to show this blank form.
    while not anvil.users.get_user():
      anvil.users.login_with_form(show_signup_option=False)
    self.card_1.visible = True
    self.init_dict = anvil.server.call('init')
    if parameters.DEBUG_MODE:
      self.enter_button_click()
    else:
      self.enter_button.visible = True

  def enter_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    glob.name = self.init_dict['name']
    glob.trust_level = self.init_dict['trust_level']
    if self.init_dict['state']['status'] == "matched":
      item = {k: self.init_dict['state'][k] for k in MatchForm.state_keys}
      open_form(MatchForm(item=item))
    else:
      open_form('MenuForm', item=self.init_dict)

