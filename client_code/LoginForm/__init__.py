from ._anvil_designer import LoginFormTemplate
from anvil import *
import anvil.users
import anvil.server
import time
from .. import rosenberg
from datetime import date, datetime
from .. import parameters
from .. import ui_procedures as ui
from anvil_extras import augment


class LoginForm(LoginFormTemplate):
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.quote_label.text = rosenberg.quote_of_the_day(date.today())
    
  def form_show(self, **event_args):
    # Do the code here to show this blank form.
    while not anvil.users.get_user():
      user = anvil.users.login_with_form(show_signup_option=False)
      if user and (not user['password_hash']) and (not user['init_date']):
        anvil.users.logout()
        with Notification("Creating a new account requires an invite link."):
          anvil.server.call_s('remove_user', user)
          time.sleep(2)  
    self.card_1.visible = True
    self.init_dict = ui.get_init()
    if parameters.DEBUG_MODE:
      self.enter_button_click()
    else:
      self.enter_button.visible = True
      self.enter_button.trigger('focus')

  def enter_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    ui.reload(self.init_dict)


