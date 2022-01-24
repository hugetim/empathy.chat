from ._anvil_designer import LoginFormTemplate
from anvil import *
import anvil.users
import anvil.server
from .. import rosenberg
from datetime import date


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
      if user and (not user['init_date']):
        anvil.users.logout()
        with Notification("Creating a new account requires an invite link."):
          anvil.server.call_s('remove_user', user)
          import time
          time.sleep(2)  
    self.card_1.visible = True
    from .. import ui_procedures as ui
    self.init_dict = ui.get_init()
    from .. import parameters
    if parameters.DEBUG_MODE:
      self.enter_button_click()
    else:
      from anvil_extras import augment
      self.enter_button.visible = True
      self.enter_button.trigger('focus')

  def enter_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    from .. import ui_procedures as ui
    ui.reload(self.init_dict)
    from .. import glob
    if glob.MOBILE and self.init_dict['state']['status'] not in ["matched", "requesting", "pinged"]:
      Notification("empathy.chat works OK on mobile but may be easier on a computer", 
                   timeout=4, style="warning").show()


