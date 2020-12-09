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
from .... import timeproposals as t
import datetime


class CreateForm(CreateFormTemplate):
  @staticmethod
  def proposal_to_item(proposal):
    item = {key: value for (key, value) in proposal.items() if key not in ['cancel_buffer',
                                                                           'cancel_date']}
    if proposal['cancel_buffer'] in t.CANCEL_TEXT.keys():
      item['cancel_buffer'] = proposal['cancel_buffer']
      item['cancel_date'] = None
    else:
      item['cancel_buffer'] = "custom"
      item['cancel_date'] = item['start_date'] - datetime.timedelta(minutes=proposal['cancel_buffer'])
    return item
      
  @staticmethod
  def item_to_proposal(item):
    proposal = {key: value for (key, value) in item.items() if key not in ['cancel_buffer']}
    if item['cancel_buffer'] != "custom":
      proposal['cancel_buffer'] = item['cancel_buffer']
    else:
      delta = item['start_date'] - item['cancel_date']
      proposal['cancel_buffer'] = delta.total_seconds() / 60
    return proposal   
      
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    #alert title: New Empathy Chat Proposal
    #alert buttons: OK, Cancel
    
    # Any code you write here will run when the form opens.
    self.drop_down_start.items = [("now", 1), ("later...", 0)]
    self.drop_down_duration.items = list(zip(t.DURATION_TEXT.values(), t.DURATION_TEXT.keys()))
    self.drop_down_cancel.items = list(zip(t.CANCEL_TEXT.values(), t.CANCEL_TEXT.keys()))
    self.drop_down_eligible.items = [("Anyone (up to 3 degrees separation)", 3),
                                     ('"Friends of friends" (2 degrees separation)', 2),
                                     ("Direct connections only (1st degree)", 1),
                                     ("Specific 1st degree connection(s)...",0)
                                    ]
    self.standardize_values()
    self.date_picker_start_initialized = False
    self.date_picker_cancel_initialized = False
    if not self.item['start_now']:
      self.drop_down_start_change()
    self.repeating_panel_1.set_event_handler('x-remove', self.remove_alternate)

  def standardize_values(self):
    if self.item['duration'] not in t.DURATION_TEXT.keys():
      self.drop_down_duration.selected_value = t.closest_duration(self.item['duration'])
    if self.item['cancel_buffer'] not in t.CANCEL_TEXT.keys():
      self.date_picker_cancel.date = (self.item['start_date'] 
                                      - datetime.timedelta(minutes=self.item['cancel_buffer']))
      self.drop_down_cancel.selected_value = "custom"
  
  def init_date_picker_start(self):
    self.date_picker_start.min_date = t.DEFAULT_START_MIN
    self.date_picker_start.max_date = t.DEFAULT_START_MAX
    if not self.date_picker_start.date:
       self.date_picker_start.date = t.DEFAULT_ITEM['start_date']
    self.date_picker_start_initialized = True
    
  def init_date_picker_cancel(self):
    self.date_picker_cancel.min_date = h.now()
    self.date_picker_cancel.max_date = self.date_picker_start.max_date
    self.date_picker_cancel.date = t.default_cancel_date(h.now(), self.date_picker_start.date)
    self.date_picker_cancel_initialized = True

  def update_cancel_visibility(self):
      if self.item['start_now']:
        self.set_item_alt()
        if not self.item['alt']:
          self.column_panel_cancel.visible = False
        else:
          # this keeps the "Cancel" column heading for the alternatives
          self.column_panel_cancel.visible = True
          self.drop_down_cancel.visible = False
          self.date_picker_cancel.visible = False
      else:
        self.column_panel_cancel.visible = True
        self.drop_down_cancel.visible = True
        self.drop_down_cancel_change()
    
  def drop_down_start_change(self, **event_args):
    """This method is called when an item is selected"""
    if self.item['start_now']: #self.drop_down_start.selected_value == 0:
      self.date_picker_start.visible = False
      self.update_cancel_visibility()
    else:
      if not self.date_picker_start_initialized:
        self.init_date_picker_start()
      self.check_times()
      self.date_picker_start.visible = True
      self.update_cancel_visibility()

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
##### Continue refactor here ###################################################################3    
  def check_times(self):
    if self.drop_down_start == "now":
      return True
    else:
      if self.date_picker_start.date < (h.now() 
                                          + datetime.timedelta(minutes=t.CANCEL_MIN_MINUTES)):
        self.label_start.text = "The Start Time must be at least " + str(t.CANCEL_MIN_MINUTES) + " minutes away."
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
          self.label_cancel.text = 'The "Cancel" time must be prior to the Start Time (by at least ' + str(t.CANCEL_MIN_MINUTES) + ' minutes).'
          self.label_cancel.visible = True
          return False
        elif (cancel_date > self.date_picker_start.date 
                            - datetime.timedelta(minutes=t.CANCEL_MIN_MINUTES)):
          self.label_cancel.text = 'The "Cancel" time must be at least ' + str(t.CANCEL_MIN_MINUTES) + ' minutes prior to the Start Time.'
          self.label_cancel.visible = True
          return False
        else:
          self.label_cancel.visible = False
          return True

  def button_add_alternate_click(self, **event_args):
    """This method is called when the button is clicked"""
    if not self.repeating_panel_1.items:
      if self.drop_down_start.selected_value == 0:
        start_1 = self.date_picker_start.date
      else:
        start_1 = h.now()
      self.repeating_panel_1.items = [{'start': (start_1 
                                                 + datetime.timedelta(minutes=t.DEFAULT_NEXT_MINUTES)), 
                                       'duration': self.drop_down_duration.selected_value, 
                                       'cancel_drop': self.drop_down_cancel.selected_value,
                                      }]
      self.update_cancel_visibility()
    else:
      previous_item = self.repeating_panel_1.items[-1]
      self.repeating_panel_1.items += [{'start': (previous_item['start']
                                                  + datetime.timedelta(minutes=t.DEFAULT_NEXT_MINUTES)), 
                                        'duration': previous_item['duration'], 
                                        'cancel_drop': previous_item['cancel_drop'],
                                       }]
    if len(self.repeating_panel_1.items) == 4:
      self.button_add_alternate.visible = False
      
  def remove_alternate(self, item_to_remove, **event_args):
    self.repeating_panel_1.items.remove(item_to_remove)
    self.update_cancel_visibility()

  def drop_down_eligible_change(self, **event_args):
    """This method is called when an item is selected"""
    if self.drop_down_eligible.selected_value == 0:
      self.multi_select_drop_down.visible = True
    else:
      self.multi_select_drop_down.visible = False

  def set_item_alt(self):
    self.item['alt'] = self.repeating_panel_1.items