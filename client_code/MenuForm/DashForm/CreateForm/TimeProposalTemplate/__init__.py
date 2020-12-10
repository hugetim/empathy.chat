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

  def form_show(self, **event_args):
    """This method is called when the column panel is shown on the screen"""
    self.update()  
    
  def normalize_initial_state(self):
    if self.item['duration'] not in t.DURATION_TEXT.keys():
      self.item['duration'] = t.closest_duration(self.item['duration'])
    if self.item['cancel_buffer'] not in t.CANCEL_TEXT.keys():
      self.item['cancel_date'] = (self.item['start_date'] 
                                  - datetime.timedelta(minutes=self.item['cancel_buffer']))
      self.item['cancel_buffer'] = "custom"
  
  def init_date_picker_start(self):
    self.date_picker_start.min_date = t.DEFAULT_START_MIN
    self.date_picker_start.max_date = t.DEFAULT_START_MAX
    
  def init_date_picker_cancel(self):
    self.date_picker_cancel.min_date = h.now()
    self.date_picker_cancel.max_date = self.date_picker_start.max_date
    if not self.item['cancel_date']:
      self.item['cancel_date'] = t.default_cancel_date(h.now(), self.item['start_date'])
    self.date_picker_cancel_initialized = True

  def update(self):
    if self.drop_down_cancel.selected_value == "custom":
      if not self.date_picker_cancel_initialized:
        self.init_date_picker_cancel()
      self.date_picker_cancel.visible = True
    else:
      self.date_picker_cancel.visible = False
    self.parent.raise_event('x-update')
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
    
  def check_times(self):
    self.label_start.visible = False
    self.label_cancel.visible = False
    messages = t.get_proposal_times_errors(h.now(), self.proposal())
    if 'start_date' in messages:
      self.label_start.text = messages['start_date']
      self.label_start.visible = True
    elif 'cancel_buffer' in messages:
      self.label_cancel.text = messages['cancel_buffer']
      self.label_cancel.visible = True

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
