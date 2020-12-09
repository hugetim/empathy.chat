from ._anvil_designer import TimeProposalTemplateTemplate
from anvil import *
import anvil.server
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users
from ..... import helper as h
from ..... import parameters as p
from ..... import timeproposals as t
import datetime
from .. import CreateForm


class TimeProposalTemplate(TimeProposalTemplateTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.drop_down_duration.items = [(t.DURATION_TEXT[m], m) 
                                       for m in range(15, 75, 10)]
    self.drop_down_duration.selected_value = self.item['duration']
    self.CANCEL_MIN_MINUTES = t.CANCEL_MIN_MINUTES
    self.CANCEL_DEFAULT_MINUTES = t.CANCEL_DEFAULT_MINUTES
    self.drop_down_cancel.items = [(t.CANCEL_TEXT[m], m)
                                   for m in t.CANCEL_TEXT.keys()]
    self.drop_down_cancel.selected_value = self.item['cancel_drop']
    self.init_date_picker_start(self.item['start'])
    self.date_picker_cancel_initialized = False
    self.drop_down_cancel_change()
    
  def init_date_picker_start(self, start):
    self.date_picker_start.min_date = (h.now() 
                                       + datetime.timedelta(seconds=max(p.WAIT_SECONDS,
                                                                        60*self.CANCEL_MIN_MINUTES)))
    self.date_picker_start.max_date = h.now() + datetime.timedelta(days=31)
    self.date_picker_start.date = start
    self.date_picker_start_initialized = True
    
  def init_date_picker_cancel(self):
    self.date_picker_cancel.min_date = h.now()
    self.date_picker_cancel.max_date = self.date_picker_start.max_date
    init_minutes_prior = max(self.CANCEL_MIN_MINUTES,
                             min(self.CANCEL_DEFAULT_MINUTES,
                             ((self.date_picker_start.date - h.now()).seconds/60)/2))
    self.date_picker_cancel.date = (self.date_picker_start.date 
                                      - datetime.timedelta(minutes=init_minutes_prior))
    self.date_picker_cancel_initialized = True

  def drop_down_cancel_change(self, **event_args):
    """This method is called when an item is selected"""
    if self.drop_down_cancel.selected_value == "custom":
      if not self.date_picker_cancel_initialized:
        self.init_date_picker_cancel()
      self.date_picker_cancel.visible = True
    else:
      self.date_picker_cancel.visible = False
    self.check_times()
    self.item['cancel_drop'] = self.drop_down_cancel.selected_value

  def date_picker_start_change(self, **event_args):
    """This method is called when the selected date changes"""
    self.check_times()
    self.item['start'] = self.date_picker_start.date

  def date_picker_cancel_change(self, **event_args):
    """This method is called when the selected date changes"""
    self.check_times()    
    
  def check_times(self):
    if self.date_picker_start.date < (h.now() 
                                        + datetime.timedelta(minutes=self.CANCEL_MIN_MINUTES)):
      self.label_start.text = "The Start Time must be at least " + str(self.CANCEL_MIN_MINUTES) + " minutes away."
      self.label_start.visible = True
      self.label_cancel.visible = False
      return False
    else:
      self.label_start.visible = False
      if self.drop_down_cancel.selected_value == "custom":
        cancel_date = self.date_picker_cancel.date
      else:
        minutes_prior = self.drop_down_cancel.selected_value
        cancel_date = (self.date_picker_start.date 
                      - datetime.timedelta(minutes=minutes_prior))
      if cancel_date < h.now():
        self.label_cancel.text = 'The specified "Cancel" time has already passed.'
        self.label_cancel.visible = True
        return False
      elif (cancel_date > self.date_picker_start.date):
        self.label_cancel.text = 'The "Cancel" time must be prior to the Start Time (by at least ' + str(self.CANCEL_MIN_MINUTES) + ' minutes).'
        self.label_cancel.visible = True
        return False
      elif (cancel_date > self.date_picker_start.date 
                          - datetime.timedelta(minutes=self.CANCEL_MIN_MINUTES)):
        self.label_cancel.text = 'The "Cancel" time must be at least ' + str(self.CANCEL_MIN_MINUTES) + ' minutes prior to the Start Time.'
        self.label_cancel.visible = True
        return False
      else:
        self.label_cancel.visible = False
        return True

  def drop_down_duration_change(self, **event_args):
    """This method is called when an item is selected"""
    self.item['duration'] = self.drop_down_duration.selected_value

  def button_1_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.parent.raise_event('x-remove', item_to_remove=self.item)
    self.remove_from_parent()


