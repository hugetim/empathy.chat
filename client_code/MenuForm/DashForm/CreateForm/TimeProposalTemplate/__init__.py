from ._anvil_designer import TimeProposalTemplateTemplate
from anvil import *
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
    self.init_date_picker_start()
    
  def form_show(self, **event_args):
    """This method is called when the column panel is shown on the screen"""
    self.alert_form = get_open_form().proposal_alert
    self.update()
     
  def init_date_picker_start(self):
    defaults = t.ProposalTime.default_start()
    self.date_picker_start.min_date = defaults['s_min']
    self.date_picker_start.max_date = defaults['s_max']
    
  def update(self):
    self.check_times()
    self.refresh_data_bindings()
        
  def date_picker_start_change(self, **event_args):
    """This method is called when the selected date changes"""
    self.update()
   
  def check_times(self):
    self.label_start.visible = False
    self.alert_form.label_cancel.visible = False
    messages = self.proptime().get_errors(self.alert_form.item['conflict_checks'])
    if messages:
      self.update_save_ready(False)
      if 'start_date' in messages:
        self.label_start.text = messages['start_date']
        self.label_start.visible = True
      elif 'cancel_buffer' in messages:
        self.alert_form.label_cancel.text = messages['cancel_buffer']
        self.alert_form.label_cancel.visible = True
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
