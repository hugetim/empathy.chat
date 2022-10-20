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
      [(item['prop'].start_now and item['prop'].specific_user_eligible)
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
        anvil.server.call('save_name', edit_form.item)
        self.top_form.item['name'] = edit_form.item['first']
    name = self.top_form.item['name']
    if name:
      self.welcome_label.text = "Hi, " + name + "!"
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
    self.repeating_panel_1.items = sorted(deepcopy(self.item['proposals']), key=lambda x:x['prop_time'].start_for_order)
    self.data_grid_1.visible = bool(self.item['proposals'])
    others_props_visible = (self.data_grid_1.visible
                            and any([not item['prop'].own
                                     for item in self.item['proposals']]))
    own_props_visible = (self.data_grid_1.visible
                         and any([item['prop'].own
                                  for item in self.item['proposals']]))
    self.status_label.bold = False
    if own_props_visible and not others_props_visible:
      self.status_label.text = "Your current empathy chat requests:"
      self.status_label.align = "left"
      self.status_label.role = ""
      self.status_label.spacing_below = "none"
      self.status_label.visible = True
    elif others_props_visible:
      now_prop_visible = any([item['prop'].start_now
                              for item in self.item['proposals']])
      later_prop_visible = any([not item['prop'].start_now
                                for item in self.item['proposals']])
      if later_prop_visible and not now_prop_visible:
        self.status_label.text = "You can accept an existing empathy chat request or create your own."
      elif not later_prop_visible and now_prop_visible:
        self.status_label.text = "You can join an empathy chat now or create a new empathy chat request."
        self.status_label.bold = True
      else:
        self.status_label.text = (
          "You can join an empathy chat now, accept a request to chat later, or create a new empathy chat request."
        )
        self.status_label.bold = True
      self.status_label.align = "center"
      self.status_label.role = "subheading"
      self.status_label.spacing_below = "small"
      self.status_label.visible = True
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
    """This method is called every 5 seconds, checking for status changes"""
    state = anvil.server.call_s('get_state')
    self.update_status(state)    

  def get_conflict_checks(self):
    conflict_checks = [{'start': match_dict['start_date'],
                        'end': (match_dict['start_date']
                                + timedelta(minutes=match_dict['duration_minutes']))} 
                       for match_dict in self.item['upcomings']]
    for port_prop in t.Proposal.props_from_view_items(self.item['proposals']):
      conflict_checks += port_prop.get_check_items()
    
  def propose_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    with h.PausedTimer(self.timer_2), h.Disabled(self.propose_button):
      self.propose()
    
  def propose(self, specified_users=[], link_key=""):
    if link_key:
      new_prop = t.Proposal(eligible=0, eligible_starred=False)
      form_item = new_prop.create_form_item("now not allowed",
                                            self.get_conflict_checks())
      form_item['user_items'] = []
      form_item['group_items'] = []
    else:
      new_prop = t.Proposal()
      form_item = new_prop.create_form_item(self.item['status'],
                                            self.get_conflict_checks())
    if specified_users:
      form_item['eligible'] = 0
      form_item['eligible_users'] = specified_users
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
      self._handle_prop_call(*anvil.server.call('add_proposal', proposal, link_key=link_key))
      
  def _handle_prop_call(self, state, prop_id):
    if prop_id is None:
      Notification("Matching you with another user ready to start an empathy chat now...",timeout=5).show()
    self.update_status(state)

  def edit_proposal(self, prop_id):
    """This method is called when the button is clicked"""
    prop_to_edit = self._prop_from_id(prop_id)
    form_item = prop_to_edit.create_form_item(self.item['status'],
                                              self.get_conflict_checks())
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
