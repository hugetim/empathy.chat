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
  CANCEL_MIN_MINUTES = 5
  CANCEL_DEFAULT_MINUTES = 15
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
  
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    
    #alert title: New Empathy Chat Proposal
    #alert buttons: OK, Cancel
    self.drop_down_duration.items = [(h.DURATION_TEXT[m], m) 
                                       for m in range(15, 75, 10)]
    self.drop_down_duration.selected_value = 25

    self.drop_down_cancel.items = [(self.CANCEL_TEXT[m], m)
                                   for m in (5, 15, 30, 60, 120, 8*60, 24*60, 48*60)]
    self.drop_down_cancel.items += [(self.CANCEL_TEXT["custom"],"custom")]
    self.drop_down_cancel.selected_value = self.CANCEL_DEFAULT_MINUTES
    self.drop_down_eligible.items = [("Allow anyone to accept (up to 3rd degree connections)", 3),
                                     ("Limit to 2nd degree connections (or closer)", 2),
                                     ("Limit to 1st degree connections", 1)]
    self.date_picker_start_initialized = False
    self.date_picker_cancel_initialized = False
    self.repeating_panel_1.set_event_handler('x-remove', self.remove_alternate)
    
  def init_date_picker_start(self):
    self.date_picker_start.min_date = (h.now() 
                                       + datetime.timedelta(seconds=max(p.WAIT_SECONDS,
                                                                          60*self.CANCEL_MIN_MINUTES)))
    self.date_picker_start.max_date = h.now() + datetime.timedelta(days=31)
    self.date_picker_start.date = (h.now() 
                                   + datetime.timedelta(minutes=p.DEFAULT_NEXT_MINUTES))
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
    
  def drop_down_start_change(self, **event_args):
    """This method is called when an item is selected"""
    if self.drop_down_start.selected_value == "later...":
      if not self.date_picker_start_initialized:
        self.init_date_picker_start()
      self.check_times()
      self.date_picker_start.visible = True
      self.column_panel_cancel.visible = True
      self.drop_down_cancel.visible = True
      self.drop_down_cancel_change()
    else:
      self.date_picker_start.visible = False
      if not self.repeating_panel_1.items:
        self.column_panel_cancel.visible = False
      else:
        self.drop_down_cancel.visible = False
        self.date_picker_cancel.visible = False

  def drop_down_cancel_change(self, **event_args):
    """This method is called when an item is selected"""
    if self.drop_down_cancel.selected_value == "custom":
      if not self.date_picker_cancel_initialized:
        self.init_date_picker_cancel()
      self.date_picker_cancel.visible = True
    else:
      self.date_picker_cancel.visible = False
    self.check_times()

  def date_picker_start_change(self, **event_args):
    """This method is called when the selected date changes"""
    self.check_times()

  def date_picker_cancel_change(self, **event_args):
    """This method is called when the selected date changes"""
    self.check_times()    
    
  def check_times(self):
    if self.drop_down_start == "now":
      return True
    else:
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

  def button_add_alternate_click(self, **event_args):
    """This method is called when the button is clicked"""
    if not self.repeating_panel_1.items:
      if self.drop_down_start.selected_value == "later...":
        start_1 = self.date_picker_start.date
      else:
        start_1 = h.now()
        self.column_panel_cancel.visible = True
        self.drop_down_cancel.visible = False
        self.date_picker_cancel.visible = False
      self.repeating_panel_1.items = [{'start': (start_1 
                                                 + datetime.timedelta(minutes=p.DEFAULT_NEXT_MINUTES)), 
                                       'duration': self.drop_down_duration.selected_value, 
                                       'cancel_drop': self.drop_down_cancel.selected_value,
                                      }]
    else:
      previous_item = self.repeating_panel_1.items[-1]
      self.repeating_panel_1.items += [{'start': (previous_item['start']
                                                  + datetime.timedelta(minutes=p.DEFAULT_NEXT_MINUTES)), 
                                        'duration': previous_item['duration'], 
                                        'cancel_drop': previous_item['cancel_drop'],
                                       }]
    if len(self.repeating_panel_1.items) == 4:
      self.button_add_alternate.visible = False
      
  def remove_alternate(self, item_to_remove, **event_args):
    self.repeating_panel_1.items.remove(item_to_remove)
    if not self.repeating_panel_1.items and self.drop_down_start.selected_value != "later...":
      self.column_panel_cancel.visible = False

  def drop_down_eligible_change(self, **event_args):
    """This method is called when an item is selected"""
    if self.drop_down_eligible.selected_value == "Select specific 1st degree connection(s)":
      self.multi_select_drop_down.visible = True
    else:
      self.multi_select_drop_down.visible = False

