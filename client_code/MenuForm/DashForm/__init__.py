from ._anvil_designer import DashFormTemplate
from anvil import *
import anvil.server
from .CreateForm import CreateForm
from ... import timeproposals as t


class DashForm(DashFormTemplate):
  def __init__(self, name, tallies, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
    
    if name:
      self.welcome_label.text = "Hi, " + name + "!"
    self.tallies = tallies
    self.timer_2.interval = 5
       
  def form_show(self, **event_args):
    """This method is called when the HTML panel is shown on the screen"""
    self.top_form = get_open_form()
    self.update_tally_label()

  def timer_2_tick(self, **event_args):
    """This method is called every 5 seconds, checking for status changes"""
    # Run this code approx. once a second
    self.tallies = anvil.server.call_s('get_tallies')
    self.update_tally_label()    
    
  def update_tally_label(self):
    """Update form based on tallies state"""
    pass

  def row_from_prop_dict(self, prop_dict):
    row = {users: }
    
  def propose_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    content = CreateForm(item=CreateForm.proposal_to_item(t.DEFAULT_PROPOSAL))
    self.top_form.proposal_alert = content
    out = alert(content=self.top_form.proposal_alert,
                title="New Empathy Chat Proposal",
                large=True,
                dismissible=False,
                buttons=[])
    print(out is True)
    if out is True:
      proposal = content.proposal()
      s, sl, self.tallies = anvil.server.call('add_request', proposal)
      self.top_form.set_seconds_left(s, sl)
      self.top_form.reset_status()
      if (not proposal['start_now']) or proposal['alt']:
        alert(title='"later" proposals not implemented yet')
