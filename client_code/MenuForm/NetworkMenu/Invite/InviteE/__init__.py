from ._anvil_designer import InviteETemplate
from anvil import *
import anvil.users
import anvil.server
from ..... import portable as t
from datetime import timedelta
from ....DashForm.CreateForm import CreateForm


class InviteE(InviteETemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.

  def not_now_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.parent.raise_event("x-close-alert", value=True)  

  def propose_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    state = anvil.server.call('get_status')
    top_form = get_open_form()
    top_form.reset_status(state)
    self.parent.raise_event("x-close-alert", value=True) 
    if state['status'] not in ["pinging", "matched"]:
      top_form.content.propose(link_key=self.item['link_key'])
    else:
      alert("Unable to propose exchange just now. Please try again later.")
