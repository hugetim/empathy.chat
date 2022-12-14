from ._anvil_designer import InvitesTemplate
from anvil import *
from .... import glob
from .... import invite_controller


class Invites(InvitesTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.update()
    
  def update(self):
    self.invite_button.visible = glob.trust_level >= 3
    glob.invites = invite_controller.load_invites()
    self.invites_data_grid.visible = glob.invites
    if glob.invites:
      self.invites_repeating_panel.items = glob.invites

  def invite_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    from .... import prompts
    prompts.invite_dialog()
    self.update()

