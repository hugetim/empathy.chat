from ._anvil_designer import DashFormTemplate
from anvil import *
import anvil.server
from .CreateForm import CreateForm
from .TimerForm import TimerForm
from ... import timeproposals as t
from ... import helper as h
from ... import parameters as p


class DashForm(DashFormTemplate):
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
    
    self.timer_2.interval = 5
       
  def form_show(self, **event_args):
    """This method is called when the HTML panel is shown on the screen"""
    self.top_form = get_open_form()
    name = self.top_form.item['name']
    if name:
      self.welcome_label.text = "Hi, " + name + "!"
    self.update_form()

  def update_form(self):
    if self.item['status'] == "pinged":
      self.confirm_match(self.item['seconds_left'])
    else:
      self.update_proposal_table()
      
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
    
  def update_proposal_table(self):
    """Update form based on proposals state"""
    if self.item['proposals']:
      items = []
      own_count = 0
      for prop in self.item['proposals']:
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
      self.update_status(anvil.server.call('add_proposal', proposal))

  def edit_proposal(self, prop_id):
    """This method is called when the button is clicked"""
    [prop_to_edit] = [prop for prop in self.item['proposals'] 
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
      
  def update_status(self, state):
    self.item['proposals'] = state['proposals']
    self.set_seconds_left(state['status'], state['seconds_left'])
    if self.item['status'] in [None, "requesting", "pinged"]:
      self.update_form()
    else:
      self.top_form.reset_status(state)

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
        state = anvil.server.call('match_commenced')
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
    