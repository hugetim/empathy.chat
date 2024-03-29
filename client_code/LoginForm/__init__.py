from ._anvil_designer import LoginFormTemplate
from anvil import *


class LoginForm(LoginFormTemplate):
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    
  def form_show(self, **event_args):
    # Do the code here to show this blank form.
    self._login_sequence()
    
  def _login_sequence(self):
    from .. import ui_procedures as ui
    from .. import glob
    user, user_id = ui.get_user_and_id()
    if user:
      self.rich_text_1.visible = False
      self.card_1.visible = True
      glob.logged_in_user = user
      glob.logged_in_user_id = user_id
      self._load_user()
    else:
      self.login_button.visible = True
      self.rich_text_1.visible = True

  def _load_user(self):
    from .. import ui_procedures as ui
    self.new_form, self.init_dict = ui.init_load(reload=False)
    from .. import parameters
    if parameters.DEBUG_MODE:
      self.enter_button_click()
    else:
      from anvil_extras import augment
      self.enter_button.visible = True
      self.enter_button.trigger('focus')
  
  def enter_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    open_form(self.new_form)
    from .. import glob
    if glob.MOBILE and self.init_dict['state']['status'] not in ["matched", "requesting", "pinged"]:
      Notification("empathy.chat should work on a mobile device, but some bits function better on a computer.", 
                   timeout=4, style="info").show()

  def timer_1_tick(self, **event_args):
    """Async loading of Rosenberg quote, other"""
    from .. import rosenberg
    from datetime import date
    from .. import ui_procedures as ui
    self.quote_label.text = rosenberg.quote_of_the_day(date.today())
    ui.get_mobile_status()
    from .. import parameters
    self.timer_1.interval = 0

  def login_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self._login_sequence()
