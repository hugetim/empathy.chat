from ._anvil_designer import Invited2Template
from anvil import *
import anvil.users
from ....MenuForm.SettingsForm.Phone import Phone


class Invited2(Invited2Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.logged_in = anvil.users.get_user()
    self.user_linear_panel.visible = self.logged_in
    self.new_linear_panel.visible = not self.logged_in

  def form_show(self, **event_args):
    """This method is called when the column panel is shown on the screen"""
    if self.logged_in:
      self.phone_form = Phone()
      self.user_linear_panel.add_component(self.phone_form)
    
  def ok_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if self.logged_in:
      if self.phone_form.item['status'] == "confirmed":
        self.parent.raise_event("x-close-alert", value=True)
      else:
        if confirm("Proceed without confirming a phone number? "
                   "If so, you may add a phone number later, in which case you will be "
                   f"connected to {self.item['inviter']} if the last 4 digits they "
                   "entered match your confirmed number."):
          self.parent.raise_event("x-close-alert", value=False)
    else:
      self.parent.raise_event("x-close-alert", value=True)

  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    anvil.server.call('cancel_invited', self.item)
    self.parent.raise_event("x-close-alert", value=False)

  def back_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    anvil.server.call('cancel_invited', self.item)
    parent = self.parent
    self.remove_from_parent()
    from ..Invited1 import Invited1
    parent.add_component(Invited1(item=self.item))



