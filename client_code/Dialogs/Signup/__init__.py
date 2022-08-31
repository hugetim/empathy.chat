from ._anvil_designer import SignupTemplate
from anvil import *
import anvil.users
from ... import ui_procedures as ui


class Signup(SignupTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.new_user = None

  def email_box_pressed_enter(self, **event_args):
    """This method is called when the user presses Enter in this text box"""
    self.raise_event('x-close-alert', value="email")

  def google_link_click(self, **event_args):
    """This method is called when the link is clicked"""
#     new_user = anvil.users.signup_with_google()
    try:
      self.new_user = anvil.users.signup_with_google()
    except anvil.users.UserExists:
      print("UserExists: Calling login_with_google")
      self.signup_err_lbl.text = "That Google account is already registered, so sign up is unnecessary. Instead, please login now."
      self.signup_err_lbl.visible = True
      self.new_user = anvil.users.login_with_google()
    if self.new_user:
      self.raise_event('x-close-alert', value="google")

  def login_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.new_user = ui.login()
    if self.new_user:
      self.raise_event('x-close-alert', value="login")
