from ._anvil_designer import TimeProposalTemplateTemplate
from anvil import *
from ..... import helper as h
from ..... import timeproposals as t
import datetime


class TimeProposalTemplate(TimeProposalTemplateTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.drop_down_duration.items = list(zip(t.DURATION_TEXT.values(), t.DURATION_TEXT.keys()))
    self.drop_down_cancel.items = list(zip(t.CANCEL_TEXT.values(), t.CANCEL_TEXT.keys()))
    self.normalize_initial_state()
    self.init_date_picker_start()
    self.date_picker_cancel_initialized = False
    self.alert_form = get_open_form().proposal_alert
    self.update()
    
  def normalize_initial_state(self):
    if self.item['duration'] not in t.DURATION_TEXT.keys():
      self.item['duration'] = t.closest_duration(self.item['duration'])
    if self.item['cancel_buffer'] not in t.CANCEL_TEXT.keys():
      self.item['cancel_date'] = (self.item['start_date'] 
                                  - datetime.timedelta(minutes=self.item['cancel_buffer']))
      self.item['cancel_buffer'] = "custom"
  
  def init_date_picker_start(self):
    defaults = t.Proposal().default_start()
    self.date_picker_start.min_date = defaults['s_min']
    self.date_picker_start.max_date = defaults['s_max']
    
  def init_date_picker_cancel(self, now=h.now()):
    self.date_picker_cancel.min_date = now
    self.date_picker_cancel.max_date = self.date_picker_start.max_date
    if not self.item['cancel_date']:
      self.item['cancel_date'] = t.default_cancel_date(now, self.item['start_date'])
    self.date_picker_cancel_initialized = True

  def update(self):
    if self.item['cancel_buffer'] == "custom":
      if not self.date_picker_cancel_initialized:
        self.init_date_picker_cancel()
      self.date_picker_cancel.visible = True
    else:
      self.date_picker_cancel.visible = False
    self.check_times()
    self.refresh_data_bindings()
      
  def drop_down_duration_change(self, **event_args):
    """This method is called when an item is selected"""
    self.update()
    
  def drop_down_cancel_change(self, **event_args):
    """This method is called when an item is selected"""
    self.update()
    
  def date_picker_start_change(self, **event_args):
    """This method is called when the selected date changes"""
    self.update()

  def date_picker_cancel_change(self, **event_args):
    """This method is called when the selected date changes"""
    self.update()    
    
  def check_times(self, now=h.now()):
    self.label_start.visible = False
    self.label_cancel.visible = False
    messages = t.get_proposal_times_errors(now, self.proposal())
    if messages:
      self.alert_form.enable_save(False)
      if 'start_date' in messages:
        self.label_start.text = messages['start_date']
        self.label_start.visible = True
      elif 'cancel_buffer' in messages:
        self.label_cancel.text = messages['cancel_buffer']
        self.label_cancel.visible = True
    else:
      self.alert_form.enable_save(True)

  def proposal(self):
    proposal = {key: value for (key, value) in self.item.items() if key not in ['cancel_buffer']}
    proposal['start_now'] = 0
    if self.item['cancel_buffer'] != "custom":
      proposal['cancel_buffer'] = self.item['cancel_buffer']
    else:
      delta = self.item['start_date'] - self.item['cancel_date']
      proposal['cancel_buffer'] = delta.total_seconds() / 60
    return proposal       

  def remove_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.parent.raise_event('x-remove', item_to_remove=self.item)
    self.remove_from_parent()
