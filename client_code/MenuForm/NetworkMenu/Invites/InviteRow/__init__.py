from ._anvil_designer import InviteRowTemplate
from anvil import *
from .....Name import Name
from ..... import ui_procedures as ui

class InviteRow(InviteRowTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    user2 = self.item.get('invitee')
    if user2:
      self.link.visible = False
      self.copy_button.visible = False
      if user2.name:
        name_item = {'name': user2.name, 'url_confirmed': user2.url_confirmed, 'user_id': user2.user_id}
        self.name = Name(item=name_item)
        self.name_or_url_flow_panel.add_component(self.name)
      else:
        self.name_or_url_flow_panel.add_component(Label(text="[user registered, name pending]"))
    else:
      self.link.url = self.item.url
      self.link.text = "Invite Link"

  def copy_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    ui.copy_to_clipboard(self.link.url, desc="The invite link")

