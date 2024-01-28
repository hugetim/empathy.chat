from ._anvil_designer import DashFormTemplate
from anvil import *
import anvil.server
from .CreateForm import CreateForm
from ..UserMenu.Profile.NameEdit import NameEdit
from ... import portable as t
from ... import helper as h
from ... import parameters as p
from ... import glob
from datetime import timedelta
from copy import deepcopy
import time

class DashForm(DashFormTemplate):
  state_keys = {'status', 'proposals', 'upcomings', 'prompts'}
  
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
    
    self.proposals_card.visible = glob.trust_level >= 2 # show if guest_allowed (timer_1)
    specific_now_prop = any(
      [item['prop'].start_now #and item['prop'].specific_user_eligible)
       for item in self.item['proposals']]
    )
    self.set_prompts_visible(not specific_now_prop)
    self.timer_2.interval = 7.5
       
  def form_show(self, **event_args):
    """This method is called when the HTML panel is shown on the screen"""
    self.top_form = get_open_form()
    if not self.top_form.item['name']:
      name_item = {'first': "",
                   'last': "",
                  }
      edit_form = NameEdit(item=name_item)
      out = alert(content=edit_form,
                  title="Please provide your name",
                  large=False,
                  dismissible=False,
                  buttons=[])
      if out is True:
        self.top_form.item['name'] = edit_form.item['first']
        glob.name = edit_form.item['first']
        user_record = glob.users[glob.logged_in_user_id]
        user_record['first'] = edit_form.item['first']
        user_record['last'] = edit_form.item['last']
        user_record['name'] = f"{user_record['first']} {user_record['last']}"
        anvil.server.call_s('save_name', edit_form.item)
    name = self.top_form.item['name']
    if name:
      self.welcome_label.text = "Hi, " + name + "."
    self.timer_1.interval = 0.1 # so it loads new name for My Profile
    self.update_form()

  def update_form(self):
    self.update_upcoming_table()
    self.update_proposal_table()

  def update_upcoming_table(self):
    """Update form based on upcoming state"""
    self.upcoming_repeating_panel.items = sorted(deepcopy(self.item['upcomings']), key=lambda x:x['start_date'])
    self.upcoming_card.visible = bool(self.item['upcomings'])
    
  def update_proposal_table(self):
    """Update form based on proposals state"""
    self.repeating_panel_1.items = sorted(deepcopy(self.item['proposals']), 
                                          key=lambda x:x['prop_time'].start_for_order)
    self.data_grid_1.visible = bool(self.item['proposals'])
    others_props_visible = (self.data_grid_1.visible
                            and any([not item['prop'].own
                                     for item in self.item['proposals']]))
    own_props_visible = (self.data_grid_1.visible
                         and any([item['prop'].own
                                  for item in self.item['proposals']]))
    self.status_label.bold = False
    self.status_label.align = "center"
    self.status_label.role = "subheading"
    self.status_label.spacing_below = "small"
    self.status_label.visible = True
    if others_props_visible:
      now_prop_visible = any([item['prop'].start_now
                              for item in self.item['proposals']])
      later_prop_visible = any([not item['prop'].start_now
                                for item in self.item['proposals']])
      if now_prop_visible:
        self.status_label.bold = True
        if later_prop_visible:
          self.status_label.text = (
            "You can join an empathy chat now, accept a request to chat later, or create a new empathy chat request."
          )
        else:
          self.status_label.text = "You can join an empathy chat now or create a new empathy chat request."
      else: # only later_prop_visible
        self.status_label.text = "You can accept an existing empathy chat request or create your own."
    elif own_props_visible:
      self.status_label.text = "Your current empathy chat requests:"
      self.status_label.align = "left"
      self.status_label.role = ""
      self.status_label.spacing_below = "none"
    else:
      self.status_label.visible = False
  
  def update_status(self, state):
    self.item['status'] = state['status']
    if self.item['status'] in [None]:
      self.item['proposals'] = state['proposals']
      self.item['upcomings'] = state['upcomings']
      self.update_form()
    else:
      self.top_form.reset_status(state)
 
  def timer_2_tick(self, **event_args):
    """This method is called every [interval] seconds, checking for status changes"""
    state = anvil.server.call_s('get_state')
    self.update_status(state)    

  def get_conflict_checks(self, edit_prop_id=None):
    conflict_checks = [{'start': match_dict['start_date'],
                        'end': (match_dict['start_date']
                                + timedelta(minutes=match_dict['duration_minutes']))} 
                       for match_dict in self.item['upcomings']]
    for port_prop in t.Proposal.props_from_view_items(self.item['proposals']):
      if port_prop.prop_id != edit_prop_id:
        conflict_checks += port_prop.get_check_items()
    return conflict_checks

  def propose_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    button_clicked = event_args['sender']
    with h.PausedTimer(self.timer_2), h.Disabled(self.propose_button), h.Disabled(self.propose_later_button):
      start_now = button_clicked == self.propose_button
      self.propose(start_now=start_now)
    
  def propose(self, specified_users=[], link_key="", start_now=None):
    if link_key:
      new_prop = t.Proposal(eligible_all=False, eligible=0, eligible_users=[], eligible_groups=[], eligible_starred=False)
      form_item = new_prop.create_form_item("now not allowed",
                                            self.get_conflict_checks())
      form_item['user_items'] = []
      form_item['group_items'] = []
    else:
      new_prop = (t.Proposal() if start_now is None 
                  else t.Proposal(times=[t.ProposalTime(start_now=start_now)]))
      form_item = new_prop.create_form_item(self.item['status'],
                                            self.get_conflict_checks())
    if specified_users:
      form_item['eligible_all'] = False
      form_item['eligible'] = 0
      form_item['eligible_users'] = specified_users
      form_item['eligible_groups'] = []
      form_item['eligible_starred'] = False
    content = CreateForm(item=form_item)
    self.top_form.proposal_alert = content
    out = alert(content=self.top_form.proposal_alert,
                title="New Empathy Chat Request",
                large=True,
                dismissible=False,
                buttons=[])
    if out is True:
      proposal = content.proposal()
      self._handle_prop_call(*anvil.server.call('add_proposal', proposal, invite_link_key=link_key))
      
  def _handle_prop_call(self, state, prop_id):
    if prop_id is None:
      Notification("Matching you with another user ready to start an empathy chat now...",timeout=5).show()
    self.update_status(state)

  def accept_proposal(self, prop_id, time_id):
    """This method is called when the button is clicked"""
    prop_to_accept = self._accept_prop_from_id(prop_id, time_id)
    form_item = prop_to_accept.create_form_item(self.item['status'],
                                                self.get_conflict_checks())
    content = CreateForm(item=form_item)
    self.top_form.proposal_alert = content
    out = alert(content=self.top_form.proposal_alert,
                title="Accept Empathy Chat Request",
                large=True,
                dismissible=False,
                buttons=[])
    if out is True:
      proposal = content.proposal()
      self._handle_prop_call(*anvil.server.call('add_proposal', proposal))
  
  def edit_proposal(self, prop_id):
    """This method is called when the button is clicked"""
    prop_to_edit = self._prop_from_id(prop_id)
    form_item = prop_to_edit.create_form_item(self.item['status'],
                                              self.get_conflict_checks(edit_prop_id=prop_id))
    content = CreateForm(item=form_item)
    self.top_form.proposal_alert = content
    out = alert(content=self.top_form.proposal_alert,
                title="Edit Empathy Chat Request",
                large=True,
                dismissible=False,
                buttons=[])
    if out is True:
      proposal = content.proposal()
      self._handle_prop_call(*anvil.server.call('edit_proposal', proposal))

  def start_now(self, prop_id):
    proposal = self._prop_from_id(prop_id)
    proposal.times = proposal.times[0:1]
    proposal.times[0].start_now = True
    self._handle_prop_call(*anvil.server.call('edit_proposal', proposal))

  def _prop_from_id(self, prop_id):
    props_to_edit = [prop_item['prop'] for prop_item in self.item['proposals'] 
                     if prop_item['prop'].prop_id == prop_id]
    return props_to_edit[0]

  def _accept_prop_from_id(self, prop_id, time_id):
    props = [prop_item['prop'] for prop_item in self.item['proposals']
             if prop_item['prop'].prop_id == prop_id]
    new_prop = deepcopy(props[0])
    new_prop.times = [time for time in new_prop.times if time.time_id == time_id]
    new_prop.prop_id = None
    new_prop.times[0].time_id = None
    new_prop.eligible_all = True
    return new_prop
  
  def prompts_open_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    current = self.prompts_repeating_panel.visible
    self.set_prompts_visible(not current)
  
  def set_prompts_visible(self, visible):
    self.prompts_repeating_panel.visible = visible
    if visible:
      self.prompts_open_link.icon = "fa:chevron-down"
    else:
      self.prompts_open_link.icon = "fa:chevron-right"
        
  def timer_1_tick(self, **event_args):
    """This method is called Every [interval] seconds. Does not trigger if [interval] is 0."""
    self.timer_1.interval = 0
    if glob.trust_level == 1 and glob.user_items:
      self.proposals_card.visible = True
      self.top_form.connections_link.visible = True
