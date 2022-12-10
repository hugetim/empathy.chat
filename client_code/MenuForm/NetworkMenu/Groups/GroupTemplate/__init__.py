from ._anvil_designer import GroupTemplateTemplate
from anvil import *
from ..... import ui_procedures as ui


class GroupTemplate(GroupTemplateTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.

  def leave_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if ui.leave_flow(self.item):
      self.parent.raise_event('x-reset')
    