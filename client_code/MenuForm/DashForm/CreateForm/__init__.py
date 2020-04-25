from ._anvil_designer import CreateFormTemplate
from anvil import *
import anvil.server
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users
from .... import helper as h
from .... import parameters as p
import datetime

class CreateForm(CreateFormTemplate):
  
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    
    #alert title: New Empathy Chat Proposal
    #alert buttons: OK, Cancel
    self.drop_down_duration_1.items = [(h.DURATION_TEXT[m], m) 
                                       for m in range(15, 75, 10)]
    self.drop_down_duration_1.selected_value = 25
    self.CANCEL_MIN_MINUTES = 5
    self.CANCEL_DEFAULT_MINUTES = 15
    CANCEL_TEXT = {5: "5 min. prior",
                   15: "15 min. prior",
                   30: "30 min. prior",
                   60: "1 hr. prior",
                   120: "2 hrs. prior",
                   8*60: "8 hrs. prior",
                   24*60: "24 hrs. prior",
                   48*60: "48 hrs. prior",
                   "custom": "a specific time...",
                  }
    self.drop_down_cancel_1.items = [(CANCEL_TEXT[m], m)
                                     for m in (5, 15, 30, 60, 120, 8*60, 24*60, 48*60)]
    self.drop_down_cancel_1.items += [(CANCEL_TEXT["custom"],"custom")]
    self.drop_down_cancel_1.selected_value = self.CANCEL_DEFAULT_MINUTES
    self.drop_down_eligible.items = [("Allow anyone to accept (up to 3rd degree connections)", 3),
                                     ("Limit to 2nd degree connections (or closer)", 2),
                                     ("Limit to 1st degree connections", 1)]
    self.date_picker_start_1_initialized = False
    self.date_picker_cancel_1_initialized = False
    
  def init_date_picker_start_1(self):
    self.date_picker_start_1.min_date = (h.now() 
                                         + datetime.timedelta(seconds=max(p.WAIT_SECONDS,
                                                                          60*self.CANCEL_MIN_MINUTES)))
    self.date_picker_start_1.max_date = h.now() + datetime.timedelta(days=31)
    self.date_picker_start_1.date = (h.now() 
                                     + datetime.timedelta(minutes=p.DEFAULT_NEXT_MINUTES))
    self.date_picker_start_1_initialized = True
    
  def init_date_picker_cancel_1(self):
    self.date_picker_cancel_1.min_date = h.now()
    self.date_picker_cancel_1.max_date = self.date_picker_start_1.max_date
    init_minutes_prior = max(self.CANCEL_MIN_MINUTES,
                             min(self.CANCEL_DEFAULT_MINUTES,
                             ((self.date_picker_start_1.date - h.now()).seconds/60)/2))
    self.date_picker_cancel_1.date = (self.date_picker_start_1.date 
                                      - datetime.timedelta(minutes=init_minutes_prior))
    self.date_picker_cancel_1_initialized = True
    
  def drop_down_start_change(self, **event_args):
    """This method is called when an item is selected"""
    if self.drop_down_start.selected_value == "later...":
      if not self.date_picker_start_1_initialized:
        self.init_date_picker_start_1()
      self.check_times()
      self.date_picker_start_1.visible = True
      self.column_panel_cancel_1.visible = True
    else:
      self.date_picker_start_1.visible = False
      self.column_panel_cancel_1.visible = False

  def drop_down_cancel_1_change(self, **event_args):
    """This method is called when an item is selected"""
    if self.drop_down_cancel_1.selected_value == "custom":
      if not self.date_picker_cancel_1_initialized:
        self.init_date_picker_cancel_1()
      self.date_picker_cancel_1.visible = True
    else:
      self.date_picker_cancel_1.visible = False
    self.check_times()

  def date_picker_start_1_change(self, **event_args):
    """This method is called when the selected date changes"""
    self.date_picker_cancel_1.min_date = h.now()
    self.date_picker_cancel_1.max_date = self.date_picker_start_1.date
    self.check_times()

  def date_picker_cancel_1_change(self, **event_args):
    """This method is called when the selected date changes"""
    self.check_times()    
    
  def check_times(self):
    if self.drop_down_start == "now":
      return True
    else:
      if self.date_picker_start_1.date < (h.now() 
                                          + datetime.timedelta(minutes=self.CANCEL_MIN_MINUTES)):
        self.label_start_1.text = "The Start Time must be at least " + str(self.CANCEL_MIN_MINUTES) + " minutes away."
        self.label_start_1.visible = True
        self.label_cancel_1.visible = False
        return False
      else:
        self.label_start_1.visible = False
        if self.drop_down_cancel_1.selected_value == "custom":
          cancel_date = self.date_picker_cancel_1.date
        else:
          minutes_prior = self.drop_down_cancel_1.selected_value
          cancel_date = (self.date_picker_start_1.date 
                        - datetime.timedelta(minutes=minutes_prior))
        if cancel_date < h.now():
          self.label_cancel_1.text = 'The specified "Cancel" time has already passed.'
          self.label_cancel_1.visible = True
          return False
        elif (cancel_date > self.date_picker_start_1.date):
          self.label_cancel_1.text = 'The "Cancel" time must be prior to the Start Time (by at least ' + str(self.CANCEL_MIN_MINUTES) + ' minutes).'
          self.label_cancel_1.visible = True
          return False
        elif (cancel_date > self.date_picker_start_1.date 
                            - datetime.timedelta(minutes=self.CANCEL_MIN_MINUTES)):
          self.label_cancel_1.text = 'The "Cancel" time must be at least ' + str(self.CANCEL_MIN_MINUTES) + ' minutes prior to the Start Time.'
          self.label_cancel_1.visible = True
          return False
        else:
          self.label_cancel_1.visible = False
          return True
