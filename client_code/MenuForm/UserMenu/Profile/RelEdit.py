from ._anvil_designer import RelEditTemplate
from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users
import anvil.server
from anvil_extras.utils import wait_for_writeback
from ...NetworkMenu.Invite.InviteA.RelationshipPromptOnly import RelationshipPromptOnly
from .... import parameters as p


class RelEdit(RelEditTemplate):
  item_keys = {'prompt', 'text'}

  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    
  def form_show(self, **event_args):
    """This method is called when the column panel is shown on the screen"""
    item = {'relationship': self.item['relationship'], 'name': self.item['name']}
    self.relationship_prompt = RelationshipPromptOnly(item=item)
    self.linear_panel_1.add_component(self.relationship_prompt)
    self.relationship_prompt.add_event_handler('x-continue', self.save_button_click)
    self.relationship_prompt.relationship_text_box.set_event_handler('change', self.text_box_change)

  def text_box_change(self, **event_args):
    """This method is called when the text in this text box is edited"""
    self.save_button.enabled = self.relationship_long_enough()

  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.raise_event("x-close-alert", value=False)

  @wait_for_writeback
  def save_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if self.relationship_long_enough():
      self.item.update({'relationship': self.relationship_prompt.item['relationship']})
      self.raise_event("x-close-alert", value=True)

  def relationship_long_enough(self):
    return len(self.relationship_prompt.relationship_text_box.text) >= p.MIN_RELATIONSHIP_LENGTH
                    
                     