from ._anvil_designer import DashFormTemplate
from anvil import *
import anvil.server
from .CreateForm import CreateForm
from ... import timeproposals as t


class DashForm(DashFormTemplate):
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
    
    self.timer_2.interval = 5
       
  def form_show(self, **event_args):
    """This method is called when the HTML panel is shown on the screen"""
    self.top_form = get_open_form()
    if self.top_form.name:
      self.welcome_label.text = "Hi, " + self.top_form.name + "!"
    self.update_proposal_table()

  def timer_2_tick(self, **event_args):
    """This method is called every 5 seconds, checking for status changes"""
    # Run this code approx. once a second
    self.top_form.proposals = anvil.server.call_s('get_proposals')
    self.update_proposal_table()    
    
  def update_proposal_table(self):
    """Update form based on proposals state"""
    if self.top_form.proposals:
      items = []
      own_count = 0
      for prop in self.top_form.proposals:
        own_count += prop.own
        for time in prop.times:
          items.append({'users': prop.name, 'prop_time': time, 'prop_id': prop.prop_id,
                        'own': prop.own, 'prop_num': own_count})
      self.repeating_panel_1.items = items
    else:
      self.repeating_panel_1.items = []
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
    if out is True:
      proposal = content.proposal()
      if (not proposal.times[0].start_now) or len(proposal.times)>1:
        alert(title='"later" proposals not implemented yet')
      self.update_status(anvil.server.call('add_request', proposal))

  def edit_proposal(self, prop_id):
    """This method is called when the button is clicked"""
    [prop_to_edit] = [prop for prop in self.top_form.proposals 
                      if prop.prop_id == prop_id]
    content = CreateForm(item=prop_to_edit.create_form_item())
    self.top_form.proposal_alert = content
    out = alert(content=self.top_form.proposal_alert,
                title="Edit Empathy Chat Proposal",
                large=True,
                dismissible=False,
                buttons=[])
    if out is True:
      proposal = content.proposal()
      if (not proposal.times[0].start_now) or len(proposal.times)>1:
        alert(title='"later" proposals not implemented yet')
      self.update_status(anvil.server.call('edit_proposal', proposal))   
      
  def update_status(self, args):
    s, sl, self.top_form.proposals = args
    self.top_form.set_seconds_left(s, sl)
    if self.top_form.status not in [None, "requesting"]:
      self.top_form.reset_status()
    else:
      self.update_proposal_table()
    