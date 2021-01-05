from ._anvil_designer import ProposalRowTemplateTemplate
from anvil import *
import anvil.server
import anvil.tz
import datetime
from .... import timeproposals as t
from .... import helper as h
from ....parameters import WAIT_SECONDS, BUFFER_SECONDS


class ProposalRowTemplate(ProposalRowTemplateTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    
    # Any code you write here will run when the form opens.
    self.init()
    self.update()

  def init(self):
    if self.item['own']:
      self.item['users'] = f"My proposal #{self.item['prop_num']}"
    time = self.item['prop_time']
    self.item.update({'time_id': time.time_id,
                      'duration': t.DURATION_TEXT[time.duration],
                      'expire_date': time.expire_date,
                     })
    if time.start_now:
      self.item['start_time'] = "now"  
    else:
      start = time.start_date.astimezone(anvil.tz.tzlocal())
      self.item['start_time'] = start.strftime("%a, %b %d %I:%M%p")
    self.top_form = get_open_form()

  def update_expire_seconds(self, time_left):
    self.item['expires_in'], *rest = str(time_left).split('.')
    self.refresh_data_bindings()

  def time_left(self):
    diff = self.item['expire_date'] - h.now()
    zero = datetime.timedelta(seconds=0)
    return diff if diff > zero else zero 
    
  def update(self):
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
    self.renew_button.visible = self.item['own'] and self.item['prop_time'].start_now
    self.cancel_button.visible = self.item['own']

  def update_dash(self, state):
    self.top_form.content.update_status(state)
      
  def accept_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.update_dash(anvil.server.call('accept_proposal', 
                                       self.item['prop_time'].time_id))

  def renew_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.update_dash(anvil.server.call('confirm_wait'))

  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.update_dash(anvil.server.call('cancel', 
                                       self.item['prop_time'].time_id))

  def timer_1_tick(self, **event_args):
    """This method is called Every [interval] seconds. Does not trigger if [interval] is 0."""
    if self.top_form.content.timer_2.interval:
      self.update_expire_seconds(self.time_left())

  def edit_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.top_form.content.edit_proposal(self.item['prop_id'])


