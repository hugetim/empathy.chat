from ._anvil_designer import DashFormTemplate
from anvil import *
import anvil.server
from .CreateForm import CreateForm
from .TimerForm import TimerForm
from ..UserMenu.Profile.NameEdit import NameEdit
from ... import portable as t
from ... import helper as h
from ... import parameters as p
from datetime import timedelta
from copy import deepcopy

class DashForm(DashFormTemplate):
  state_keys = {'status', 'seconds_left', 'proposals', 'upcomings', 'prompts'}
  
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
    
    self.timer_2.interval = 5
       
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
    self.update_form()

  def update_form(self):
    if self.item['status'] == "pinged":
      self.confirm_match(self.item['seconds_left'])
    else:
      self.update_upcoming_table()
      self.update_proposal_table()

  def update_upcoming_table(self):
    """Update form based on upcoming state"""
    self.upcoming_repeating_panel.items = deepcopy(self.item['upcomings'])
    self.upcoming_card.visible = bool(self.item['upcomings'])    
    
  def update_proposal_table(self):
    """Update form based on proposals state"""
    self.repeating_panel_1.items = deepcopy(self.item['proposals'])
    self.data_grid_1.visible = bool(self.item['proposals'])
    others_props_visible = (self.data_grid_1.visible
                            and any([not item['prop'].own
                                     for item in self.item['proposals']]))
    own_props_visible = (self.data_grid_1.visible
                         and any([item['prop'].own
                                  for item in self.item['proposals']]))
    if own_props_visible:
      self.status_label.text = "Proposals:"
      self.status_label.align = "left"
      self.status_label.role = ""
      self.status_label.spacing_below = "none"
      self.status_label.visible = True
    elif others_props_visible:
      self.status_label.text = (
        "You can accept an existing proposal for an empathy chat or propose your own.")
      self.status_label.align = "center"
      self.status_label.role = "subheading"
      self.status_label.spacing_below = "small"
      self.status_label.visible = True
    else:
      self.status_label.visible = False
  
  def update_status(self, state):
    self.set_seconds_left(state['status'], state['seconds_left'])
    if self.item['status'] in [None, "requesting", "pinged"]:
      self.item['proposals'] = state['proposals']
      self.item['upcomings'] = state['upcomings']
      self.update_form()
    else:
      self.top_form.reset_status(state)
    
  def set_seconds_left(self, new_status=None, new_seconds_left=None):
    """Set status and related time variables"""
    if new_status and new_status != "matched":
      self.item['seconds_left'] = new_seconds_left
    #print('before status change: ', self.item['seconds_left'])
    self.item['status'] = new_status    
 
  def timer_2_tick(self, **event_args):
    """This method is called every 5 seconds, checking for status changes"""
    state = anvil.server.call_s('get_status')
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
    self.propose()
    
  def propose(self, specified_user=""):
    start_now = not bool(self.item['status'])
    new_prop = t.Proposal(times=[t.ProposalTime(start_now=start_now)])
    form_item = new_prop.create_form_item(self.item['status'],
                                          self.get_conflict_checks())
    if specified_user:
      form_item['eligible'] = 0
      form_item['eligible_users'] = [specified_user]
    content = CreateForm(item=form_item)
    self.top_form.proposal_alert = content
    out = alert(content=self.top_form.proposal_alert,
                title="New Empathy Chat Proposal",
                large=True,
                dismissible=False,
                buttons=[])
    if out is True:
      proposal = content.proposal()
      self.update_status(anvil.server.call('add_proposal', proposal))

  def edit_proposal(self, prop_id):
    """This method is called when the button is clicked"""
    [prop_to_edit] = [prop_item['prop'] for prop_item in self.item['proposals'] 
                      if prop_item['prop'].prop_id == prop_id]
    form_item = prop_to_edit.create_form_item(self.item['status'],
                                              self.get_conflict_checks())
    content = CreateForm(item=form_item)
    self.top_form.proposal_alert = content
    out = alert(content=self.top_form.proposal_alert,
                title="Edit Empathy Chat Proposal",
                large=True,
                dismissible=False,
                buttons=[])
    if out is True:
      proposal = content.proposal()
      self.update_status(anvil.server.call('edit_proposal', proposal))   
      
  def confirm_match(self, seconds):
    with h.PausedTimer(self.timer_2):
      f = TimerForm(seconds, self.item['status'])
      out = alert(content=f,
                  title="A match is available. Are you ready?",
                  large=False,
                  dismissible=False,
                  buttons=[("Yes", True), ("No", False)])
      if out == True:
        #self.item['status'] = "matched"
        state = anvil.server.call('match_commit')
      elif out in [False, "timer elapsed"]:
        state = anvil.server.call('cancel')
        if out == "timer elapsed":
          alert("A match was found, but the time available for you to confirm ("
                + h.seconds_to_words(p.CONFIRM_MATCH_SECONDS) + ") elapsed.",
                dismissible=False)
      else:
        if out:
          print("out:", out)
          assert out == "requesting"
        state = anvil.server.call_s('get_status')
      self.update_status(state)

  
  def prompts_open_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    current = self.prompts_repeating_panel.visible
    self.prompts_repeating_panel.visible = not current
    if current:
      self.prompts_open_link.icon = "fa:chevron-right"
    else:
      self.prompts_open_link.icon = "fa:chevron-down"
    
      
### Legacy code to be possibly repurposed ###
  def emailed_notification(self, num):
    """Return Notification (assumes num>0)"""
    if num == 1:
      message = ('Someone has been sent a '
                 + 'notification email about your request.')
      headline = 'Email notification sent'
    else:
      message = (str(num) + ' others have been sent '
                 + 'notification emails about your request.')
      headline = 'Email notifications sent'
    return Notification(message,
                        title=headline,
                        timeout=10)
###                                                        ###
    
