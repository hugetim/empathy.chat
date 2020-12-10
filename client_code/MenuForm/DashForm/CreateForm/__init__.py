from ._anvil_designer import CreateFormTemplate
from anvil import *
from .... import helper as h
from .... import timeproposals as t
import datetime


class CreateForm(CreateFormTemplate):
  
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    #alert title: New Empathy Chat Proposal
    #alert buttons: OK, Cancel
    
    # Any code you write here will run when the form opens.
    self.drop_down_start.items = [("now", 1), ("later at...", 0)]
    self.drop_down_duration.items = list(zip(t.DURATION_TEXT.values(), t.DURATION_TEXT.keys()))
    self.drop_down_cancel.items = list(zip(t.CANCEL_TEXT.values(), t.CANCEL_TEXT.keys()))
    self.drop_down_eligible.items = [("Anyone (up to 3 degrees separation)", 3),
                                     ('"Friends of friends" (2 degrees separation)', 2),
                                     ("Direct connections only (1st degree)", 1),
                                     ("Specific 1st degree connection(s)...",0)
                                    ]
    self.normalize_initial_state()
    self.date_picker_start_initialized = False
    self.date_picker_cancel_initialized = False
    self.update()
    self.repeating_panel_1.set_event_handler('x-remove', self.remove_alternate)
    self.repeating_panel_1.set_event_handler('x-update', self.sync_item_alt)

  def normalize_initial_state(self):
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
    if not self.date_picker_cancel.date:
      self.date_picker_cancel.date = t.default_cancel_date(h.now(), self.item['start_date'])
    self.date_picker_cancel_initialized = True

  def update_times(self):
    self.sync_item_alt()
    self.button_add_alternate.visible = len(self.item['alt']) < 4
    if self.item['start_now']:
      self.date_picker_start.visible = False
      if not self.item['alt']:
        self.column_panel_cancel.visible = False
      else:
        # this keeps the "Cancel" column heading for the alternatives
        self.column_panel_cancel.visible = True
        self.drop_down_cancel.visible = False
        self.date_picker_cancel.visible = False      
    else:
      if not self.date_picker_start_initialized:
        self.init_date_picker_start()
      self.date_picker_start.visible = True 
      self.column_panel_cancel.visible = True
      self.drop_down_cancel.visible = True
      if self.drop_down_cancel.selected_value == "custom":
        if not self.date_picker_cancel_initialized:
          self.init_date_picker_cancel()
        self.date_picker_cancel.visible = True
      else:
        self.date_picker_cancel.visible = False
      self.check_times()

  def update_eligible(self):
    if self.drop_down_eligible.selected_value == 0:
      self.multi_select_drop_down.visible = True
    else:
      self.multi_select_drop_down.visible = False
    
  def update(self):
    self.update_times()
    self.update_eligible()

  def drop_down_start_change(self, **event_args):
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

  def button_add_alternate_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.sync_item_alt()
    if not self.item['alt']:
      if self.item['start_now']:
        start_1 = h.now()
      else:
        start_1 = self.item['start_date']
      self.repeating_panel_1.items = [{'start_date': (start_1 
                                                      + datetime.timedelta(minutes=t.DEFAULT_NEXT_MINUTES)), 
                                       'duration': self.item['duration'], 
                                       'cancel_buffer': self.item['cancel_buffer'],
                                      }]
    else:
      previous_item = self.item['alt'][-1]
      self.repeating_panel_1.items += [{'start_date': (previous_item['start_date']
                                                  + datetime.timedelta(minutes=t.DEFAULT_NEXT_MINUTES)), 
                                        'duration': previous_item['duration'], 
                                        'cancel_buffer': previous_item['cancel_buffer'],
                                       }]
    self.update()
      
  def remove_alternate(self, item_to_remove, **event_args):
    self.repeating_panel_1.items.remove(item_to_remove)
    self.update()

  def drop_down_eligible_change(self, **event_args):
    """This method is called when an item is selected"""
    self.update()

  def sync_item_alt(self, **event_args):
    self.item['alt'] = self.repeating_panel_1.items
    
  def proposal(self):
    self.sync_item_alt()
    proposal = {key: value for (key, value) in self.item.items() if key not in ['cancel_buffer']}
    if self.item['cancel_buffer'] != "custom":
      proposal['cancel_buffer'] = self.item['cancel_buffer']
    else:
      delta = self.item['start_date'] - self.item['cancel_date']
      proposal['cancel_buffer'] = delta.total_seconds() / 60
    return proposal   
  
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
 