from ._anvil_designer import TimeProposalTemplateTemplate
from anvil import *
import anvil.users
import anvil.server
from ..... import helper as h
from ..... import portable as t
import datetime


class TimeProposalTemplate(TimeProposalTemplateTemplate):
  def proptime(self):
    return t.ProposalTime.from_create_form(self.item)

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
    defaults = t.ProposalTime.default_start()
    self.date_picker_start.min_date = defaults['s_min']
    self.date_picker_start.max_date = defaults['s_max']
    
  def init_date_picker_cancel(self):
    now=h.now()
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
    
  def check_times(self):
    self.label_start.visible = False
    self.label_cancel.visible = False
    messages = self.proptime().get_errors(self.alert_form.item['conflict_checks'])
    if messages:
      self.update_save_ready(False)
      if 'start_date' in messages:
        self.label_start.text = messages['start_date']
        self.label_start.visible = True
      elif 'cancel_buffer' in messages:
        self.label_cancel.text = messages['cancel_buffer']
        self.label_cancel.visible = True
    else:
      self.update_save_ready(True)

  def update_save_ready(self, ready):
    old = self.item['save_ready']
    self.item['save_ready'] = ready
    if ready != old:
      self.alert_form.update_save_enable()
      
  def remove_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.parent.raise_event('x-remove', item_to_remove=self.item)
    self.remove_from_parent()
