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
    if self.item['own']:
      self.users_flow_panel.add_component(Label(text=f"My request #{self.item['prop_num']}"))
    else:
      self.users_flow_panel.add_component(Name(item=prop.user))
    time = self.item['prop_time']
    self.item.update({'duration': t.DURATION_TEXT[time.duration],
                      'expire_date': time.expire_date,})
    if time.start_now:
      self.item['start_time'] = "Now"
      self.accept_button.text = "Join"
      self.accept_button.tooltip = "Click to join for an empathy chat for the duration listed"
    else:
      self.item['start_time'] = h.day_time_str(h.as_local_tz(time.start_date))
    self.top_form = get_open_form()

  def update_expire_seconds(self, time_left):
    self.item['expires_in'], *rest = str(time_left).split('.')
    self.refresh_data_bindings()

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
        days_and_hours, minutes, *rest = str(time_left).split(':')
        self.item['expires_in'] = f"{days_and_hours}:{minutes}"
    self.accept_button.visible = not self.item['own']
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


