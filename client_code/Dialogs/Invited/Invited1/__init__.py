from ._anvil_designer import Invited1Template
from anvil import *
import anvil.users
import anvil.server
import time
from ....MenuForm.NetworkMenu.Invite.InviteA.RelationshipPromptOnly import RelationshipPromptOnly
from .... import ui_procedures as ui
from .... import invited
from .... import parameters as p
from anvil_extras.utils import wait_for_writeback


class Invited1(Invited1Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.welcome_rich_text.data = dict(inviter=self.item.inviter)
    self.rich_text_1_copy.data = dict(inviter=self.item.inviter, rel_to_inviter=self.item.rel_to_inviter)
    if self.item['link_key']: # from a link invite
      self.welcome_rich_text.visible = True
      self.cancel_button.visible = False
    else:
      self.welcome_rich_text.visible = False
      self.cancel_button.visible = True

  def form_show(self, **event_args):
    """This method is called when the column panel is shown on the screen"""
    self.phone_request_label.text = (
      f"Please provide the last 4 digits of {self.item['inviter'].name}'s phone number:"
    )
    item = self.item.rel_item(for_response=True) #{'relationship': self.item['relationship'], 'name': self.item['inviter']}
    self.relationship_prompt = RelationshipPromptOnly(item=item)
    self.linear_panel_2.add_component(self.relationship_prompt)
    self.relationship_prompt.add_event_handler('x-continue', self.continue_button_click)

  def phone_last4_text_box_pressed_enter(self, **event_args):
    """This method is called when the user presses Enter in this text box"""
    self.relationship_prompt.relationship_text_box.focus()
  
  @wait_for_writeback
  def continue_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    #self.item.update({'relationship': self.relationship_prompt.item['relationship']})
    self.item.update_from_rel_item(self.relationship_prompt.item, for_response=True)
    validation_errors = self.item.invalid_response()
    if validation_errors:
      self.error("\n".join(validation_errors))
    else:
      errors = self.item.relay('respond')
      if p.MISTAKEN_INVITER_GUESS_ERROR in errors:
        errors.remove(p.MISTAKEN_INVITER_GUESS_ERROR)
        Notification(p.MISTAKEN_INVITER_GUESS_ERROR, title="Mistaken Invite", style="info", timeout=None).show()
        self.parent.raise_event("x-close-alert", value=False)
      if errors:
        self.error("\n".join(errors))
      else:
        user = anvil.users.get_user()
        has_phone = user['phone'] if user else None
        if self.item['link_key'] and not user:
          self.parent.go_invited2(self.item)
        elif self.item['link_key'] and not has_phone:
          self.parent.raise_event("x-close-alert", value=True)
        else: # connecting already-registered users
          Notification("You have been successfully connected.", style="success").show()
          self.parent.raise_event("x-close-alert", value=True)
          ui.reload()

  def error(self, text):
    self.error_label.text = text
    self.error_label.visible = True

  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.parent.raise_event("x-close-alert", value=False)
