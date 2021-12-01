from ._anvil_designer import Invited1Template
from anvil import *
import anvil.users
import anvil.server
from ..Invited2 import Invited2
from ....MenuForm.NetworkMenu.Invite.InviteA.RelationshipPromptOnly import RelationshipPromptOnly
from .... import ui_procedures as ui
from .... import parameters as p
from anvil_extras.utils import wait_for_writeback


class Invited1(Invited1Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    if self.item['link_key']: # from a link invite
      self.welcome_rich_text.visible = True
      self.cancel_button.visible = False
    else:
      self.welcome_rich_text.visible = False
      self.cancel_button.visible = True

  def form_show(self, **event_args):
    """This method is called when the column panel is shown on the screen"""
    self.phone_request_label.text = (
      f"Please provide the last 4 digits of {self.item['inviter']}'s phone number:"
    )
    item = {'relationship': self.item['relationship'], 'name': self.item['inviter']}
    self.relationship_prompt = RelationshipPromptOnly(item=item)
    self.linear_panel_2.add_component(self.relationship_prompt)
    self.relationship_prompt.add_event_handler('x-continue', self.continue_button_click)

  def phone_last4_text_box_pressed_enter(self, **event_args):
    """This method is called when the user presses Enter in this text box"""
    self.relationship_prompt.relationship_text_box.focus()
  
  @wait_for_writeback
  def continue_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.item.update({'relationship': self.relationship_prompt.item['relationship']})
    if len(self.item['phone_last4']) != 4:
      self.error("Wrong number of digits entered.")
    elif len(self.item['relationship']) < p.MIN_RELATIONSHIP_LENGTH:
      self.error("Please add a description of your relationship.")
    else:
      if self.item['link_key']: # from a link invite
        invited_item = anvil.server.call('add_invited', self.item)
      else:
        invited_item = anvil.server.call('connect_invited', self.item)
      if invited_item and self.item['link_key']:
        parent = self.parent
        self.remove_from_parent()
        self.item.update(invited_item)
        parent.add_component(Invited2(item=self.item))
      elif invited_item: # connecting already-registered users
        Notification("You have been successfully connected.", style="success").show()
        self.parent.raise_event("x-close-alert", value=True)
        ui.reload()
      else:
        self.error(f"The last 4 digits you provided do not match {self.item['inviter']}'s phone number.")

  def error(self, text):
    self.error_label.text = text
    self.error_label.visible = True

  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.parent.raise_event("x-close-alert", value=False)
