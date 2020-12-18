from ._anvil_designer import DashFormTemplate
from anvil import *
import anvil.server
from .CreateForm import CreateForm
from ... import timeproposals as t


class DashForm(DashFormTemplate):
  def __init__(self, name, proposals, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
    
    if name:
      self.welcome_label.text = "Hi, " + name + "!"
    self.proposals = proposals
    self.timer_2.interval = 5
       
  def form_show(self, **event_args):
    """This method is called when the HTML panel is shown on the screen"""
    self.top_form = get_open_form()
    self.update_proposal_table()

  def timer_2_tick(self, **event_args):
    """This method is called every 5 seconds, checking for status changes"""
    # Run this code approx. once a second
    self.proposals = anvil.server.call_s('get_proposals')
    self.update_proposal_table()    
    
  def update_proposal_table(self):
    """Update form based on proposals state"""
    for prop in self.proposals:
      print(prop.dash_rows())
    if self.proposals:
      
      self.repeating_panel_1.items = [row for row in prop.dash_rows() for prop in self.proposals]
    self.data_grid_1.visible = bool(self.repeating_panel_1.items)
  
  def propose_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    content = CreateForm(item=t.Proposal().create_form_item())
    self.top_form.proposal_alert = content
    out = alert(content=self.top_form.proposal_alert,
                title="New Empathy Chat Proposal",
                large=True,
                dismissible=False,
                buttons=[])
    print(out is True)
    if out is True:
      proposal = content.proposal()
      s, sl, self.proposals = anvil.server.call('add_request', proposal)
      self.top_form.set_seconds_left(s, sl)
      self.top_form.reset_status()
      if (not proposal.times[0].start_now) or len(proposal.times)>1:
        alert(title='"later" proposals not implemented yet')
