from ._anvil_designer import LoginFormTemplate
from anvil import *
import anvil.users
import anvil.server


class LoginForm(LoginFormTemplate):
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    
  def form_show(self, **event_args):
    # Do the code here to show this blank form.
    self.login_sequence()
    
  def login_sequence(self):
    from .. import ui_procedures as ui
    user, user_id = anvil.server.call_s('get_user', with_id=True)
    self.loading_label.visible = False
    if not user:
      self.login_button.visible = True
      self.rich_text_1.visible = True
      user = ui.login()
    if user:
      self.login_button.visible = False
      self.rich_text_1.visible = False
      self.card_1.visible = True
      from .. import glob
      glob.logged_in_user = user
      glob.logged_in_user_id = user_id
      self.init_dict = ui.get_init(spinner=False)
      ui.get_mobile_status()
      self.new_form = ui.reload(self.init_dict, do_open=False)
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
    """Async loading of Rosenberg quote"""
    from .. import rosenberg
    from datetime import date
    self.quote_label.text = rosenberg.quote_of_the_day(date.today())
    from .. import ui_procedures as ui
    from .. import parameters
    self.timer_1.interval = 0

  def login_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.login_sequence()
