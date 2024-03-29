from ._anvil_designer import PromptTemplateTemplate
from anvil import *
import anvil.server
from .... import prompts
from .... import ui_procedures as ui


class PromptTemplate(PromptTemplateTemplate):
  def __init__(self, item, **properties):
    # Set Form properties and Data Bindings.
    item = prompts.get(item)
    self.init_components(item=item, **properties)

    # Any code you write here will run when the form opens.

  def link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.item['click_fn']()

  def dismiss_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.remove_from_parent()
    anvil.server.call_s('dismiss_prompt', prompt_id=self.item['dismissable'])
    ui.init_load(spinner=False)


