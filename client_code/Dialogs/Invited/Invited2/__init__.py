from ._anvil_designer import Invited2Template
from anvil import *
import anvil.facebook.auth
import anvil.users
import anvil.server
from ....MenuForm.SettingsForm.Phone import Phone
from .... import invited


class Invited2(Invited2Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
#     self.logged_in = anvil.users.get_user()
#     self.new_linear_panel.visible = not self.logged_in
#     self.user_linear_panel.visible = self.logged_in

  def form_show(self, **event_args):
    """This method is called when the column panel is shown on the screen"""
#     if self.logged_in:
#       if self.logged_in['phone']: #prior to opportunity to confirm phone here
#         print("Warning: user already has 'phone'")
#       self.phone_form = Phone(item={"phone": ""})
#       self.user_linear_panel.add_component(self.phone_form)
    
  def ok_button_click(self, **event_args):
    """This method is called when the button is clicked"""
#     if self.logged_in and not self.logged_in['phone']:
#       if not confirm("Proceed without confirming a phone number? "
#                      "If so, you may add a phone number later, in which case you will be "
#                      f"connected to {self.item['inviter']} if the last 4 digits they "
#                      "entered match your confirmed number."):
#         return
    self.parent.raise_event("x-close-alert", value=True)

  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    invited.cancel(self.item)
    self.parent.raise_event("x-close-alert", value=False)

  def back_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    invited.cancel(self.item)
    self.parent.go_invited1(self.item)
