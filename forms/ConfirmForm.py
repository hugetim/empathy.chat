from anvil import *
import anvil.server
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.users

class ConfirmForm(ConfirmFormTemplate):
  seconds_left
  user_id
  def __init__(self, seconds_left, user_id, title="", **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
    # Any code you write here will run when the form opens.
    if title:
      self.self.label_1.text = title
    self.seconds_left = seconds_left
    self.timer_label.text = "You have " + self.seconds_left + " seconds left to confirm."
    self.user_id = user_id

  def button_yes_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.return_back(True)

  def button_no_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.return_back(False)

  def timer_1_tick(self, **event_args):
    """This method is called Every 1 seconds"""
    self.seconds_left -= 1
    self.timer_label.text = "You have " + self.seconds_left + " seconds left to confirm."
    if self.seconds_left == 0:
      self.return_back(False)
  
  def return_back(self, confirmed):
    if confirmed:
      anvil.server.call('match_commenced',self.user_id)
      open_form('Form1')
    else:
      anvil.server.call('cancel',self.user_id)
      open_form('Form1')
  
  



