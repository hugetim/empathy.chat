from ._anvil_designer import ProposalRowTemplateTemplate
from anvil import *
import anvil.users
import anvil.server
import anvil.tz
import datetime
from .... import portable as t
from .... import helper as h
from ....parameters import WAIT_SECONDS, BUFFER_SECONDS
from ....Name import Name


def own_label(prop, item):
  full_desc = prop.eligibility_desc
  abbrev_desc = full_desc if len(full_desc) < 40 else full_desc[:36] + "..."
  id_desc = unique_row_desc(prop.times, item)
  label = Label(text=f"My {id_desc} to:\n {abbrev_desc}", spacing_below="none", 
                tooltip="One of my requested times")
  if abbrev_desc != full_desc:
    label.tooltip += f", to: {full_desc}"
  return label

    
def unique_row_desc(prop_times, item):
  letter = "abcdefghijklmnopqrstuvwxyz".upper()
  if len(prop_times) > 1:
    if item['prop_count'] > 1:
      return f"#{item['prop_num']}, option {letter[item['times_i']]},"
    else:
      return f"option {letter[item['times_i']]}"
  else:
    if item['prop_count'] > 1:
      return f"request #{item['prop_num']},"
    else:
      return "request"


class ProposalRowTemplate(ProposalRowTemplateTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    
    # Any code you write here will run when the form opens.
    self.init()
    self.update()

  def init(self):    
    prop = self.item.pop('prop')
    self.item.update({'prop_id': prop.prop_id,
                      'own': prop.own,})
    time = self.item['prop_time']
    self.init_users_flow_panel(prop, time)
    self.item.update({'duration': t.DURATION_TEXT[time.duration],
                      'expire_date': time.expire_date,})
    if time.start_now:
      self.item['start_time'] = "Now (ready to start)"
      self.accept_button.text = "Join"
      self.accept_button.tooltip = "Click to join for an empathy chat for the duration listed"
    else:
      self.item['start_time'] = h.day_time_str(h.as_local_tz(time.start_date))
    self.top_form = get_open_form()

  def init_users_flow_panel(self, prop, time):
    if self.item['own']:
      self.users_flow_panel.add_component(own_label(prop, self.item))
      self.background = "theme:Light Yellow"
    else:
      self.users_flow_panel.add_component(Name(item=prop.user))
    for port_user in time.users_accepting:
      if port_user.distance == 0:
        self.users_flow_panel.add_component(Label(text="me,"), index=0)
        self.item['me_accepting'] = True
      else:
        self.users_flow_panel.add_component(Name(item=port_user))
    
  def update_expire_seconds(self, time_left):
    self.item['expires_in'] = h.seconds_to_words(time_left.total_seconds())
    self.refresh_data_bindings()

  def update_expire_if_longer(self, time_left):
    days_and_hours, minutes, *rest = str(time_left).split(':')
    if time_left >= datetime.timedelta(hours=2):
      self.item['expires_in'] = f"{days_and_hours} hours"
    else:
      self.item['expires_in'] = h.seconds_to_words(time_left.total_seconds(), include_seconds=False)
    
  def time_left(self):
    diff = self.item['expire_date'] - h.now()
    zero = datetime.timedelta(seconds=0)
    #return diff if diff > zero else zero
    return diff if diff.total_seconds() > zero.total_seconds() else zero
    
  def update(self):
    if self.item['prop_time'].start_now:
      self.timer_1.interval = 0
      self.item['expires_in'] = "n/a"
    else:
      time_left = self.time_left()
      if time_left.total_seconds() <= WAIT_SECONDS + BUFFER_SECONDS:
        self.update_expire_seconds(time_left)
        self.timer_1.interval = 1
      else:
        self.timer_1.interval = 0
        self.update_expire_if_longer(time_left)
    self.accept_button.visible = not self.item['own'] and not self.item.get('me_accepting')
    self.edit_button.visible = self.item['own']
    self.cancel_button.visible = self.item['own']

  def update_dash(self, state):
    self.top_form.content.update_status(state)
      
  def accept_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.update_dash(anvil.server.call('accept_proposal', 
                                       self.item['prop_time'].time_id))

  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.update_dash(anvil.server.call('cancel_time', 
                                       self.item['prop_time'].time_id))

  def timer_1_tick(self, **event_args):
    """This method is called Every [interval] seconds. Does not trigger if [interval] is 0."""
    timedelta_left = self.time_left()
    self.update_expire_seconds(timedelta_left)
    if timedelta_left.total_seconds() <= 0:
      self.update_dash(anvil.server.call('get_state', force_refresh=True))

  def edit_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.top_form.content.edit_proposal(self.item['prop_id'])


