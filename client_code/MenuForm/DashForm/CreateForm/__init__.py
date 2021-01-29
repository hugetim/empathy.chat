from ._anvil_designer import CreateFormTemplate
from anvil import *
import anvil.server
from .... import helper as h
from .... import portable as t
from datetime import timedelta


class CreateForm(CreateFormTemplate):
  def proposal(self):
    """Convert self.item into a proposal dictionary"""
    return t.Proposal.from_create_form(self.item)

  def proptime(self):
    return t.ProposalTime.from_create_form(self.item)
  
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    #alert title: New Empathy Chat Proposal
    #alert buttons: OK, Cancel
    
    # Any code you write here will run when the form opens.
    if self.item['now_allowed']:
      self.drop_down_start.items = [("now", 1), ("later at...", 0)]
    else:
      self.drop_down_start.items = [("later at...", 0)]
    self.drop_down_duration.items = list(zip(t.DURATION_TEXT.values(), t.DURATION_TEXT.keys()))
    self.drop_down_cancel.items = list(zip(t.CANCEL_TEXT.values(), t.CANCEL_TEXT.keys()))
    self.drop_down_eligible.items = [("Anyone (up to 3 degrees separation)", 3),
                                     ('"Friends of friends" (2 degrees separation)', 2),
                                     ("Direct connections only (1st degree)", 1),
                                     ("Specific 1st degree connection(s)...",0)
                                    ]
    self.multi_select_drop_down.items = anvil.server.call('get_port_eligible_users')
    self.normalize_initial_state()
    self.date_picker_start_initialized = False
    self.date_picker_cancel_initialized = False
    self.update()
    self.repeating_panel_1.set_event_handler('x-remove', self.remove_alternate)

  def normalize_initial_state(self):
    if self.item['duration'] not in t.DURATION_TEXT.keys():
      self.item['duration'] = t.closest_duration(self.item['duration'])
    if self.item['cancel_buffer'] not in t.CANCEL_TEXT.keys():
      self.item['cancel_date'] = (self.item['start_date'] 
                                  - timedelta(minutes=self.item['cancel_buffer']))
      self.item['cancel_buffer'] = "custom"
  
  def init_date_picker_start(self):
    defaults = t.ProposalTime.default_start()
    self.date_picker_start.min_date = defaults['s_min']
    self.date_picker_start.max_date = defaults['s_max']
    if not self.item['start_date']:
       self.item['start_date'] = defaults['start']
    self.date_picker_start_initialized = True
    
  def init_date_picker_cancel(self):
    now=h.now()
    self.date_picker_cancel.min_date = now
    self.date_picker_cancel.max_date = self.date_picker_start.max_date
    if not self.item['cancel_date']:
      self.item['cancel_date'] = t.default_cancel_date(now, self.item['start_date'])
    self.date_picker_cancel_initialized = True

  def update_times(self):
    self.button_add_alternate.visible = len(self.item['alt']) < t.Proposal.MAX_ALT_TIMES
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
      if self.item['cancel_buffer'] == "custom":
        if not self.date_picker_cancel_initialized:
          self.init_date_picker_cancel()
        self.date_picker_cancel.visible = True
      else:
        self.date_picker_cancel.visible = False
    self.check_times()
    self.refresh_data_bindings()

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
    messages = self.proptime().get_errors(self.item['conflict_checks'])
    if messages:
      self.enable_save(False)
      if 'start_date' in messages:
        self.label_start.text = messages['start_date']
        self.label_start.visible = True
      elif 'cancel_buffer' in messages:
        self.label_cancel.text = messages['cancel_buffer']
        self.label_cancel.visible = True
    else:
      self.enable_save(True)
    
  def enable_save(self, enabled):
    self.save_button.enabled = enabled
    
  def button_add_alternate_click(self, **event_args):
    """This method is called when the button is clicked"""
    if not self.item['alt']:
      if self.item['start_now']:
        start_1 = h.now()
      else:
        start_1 = self.item['start_date']
      self.item['alt'] = [{'start_date': (start_1 + t.DEFAULT_NEXT_DELTA),
                           'duration': self.item['duration'],
                           'cancel_buffer': self.item['cancel_buffer'],
                           'cancel_date': None,
                           'time_id': None,
                           'conflict_checks': self.item['conflict_checks'],
                          }]
    else:
      previous_item = self.item['alt'][-1]
      self.item['alt'] += [{'start_date': (previous_item['start_date']
                                           + t.DEFAULT_NEXT_DELTA),
                            'duration': previous_item['duration'],
                            'cancel_buffer': previous_item['cancel_buffer'],
                            'cancel_date': None,
                            'time_id': None,
                            'conflict_checks': self.item['conflict_checks'],
                           }]
    self.update()
      
  def remove_alternate(self, item_to_remove, **event_args):
    self.item['alt'].remove(item_to_remove)
    self.update()

  def drop_down_eligible_change(self, **event_args):
    """This method is called when an item is selected"""
    self.update()

  def save_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.raise_event("x-close-alert", value=True)

  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.raise_event("x-close-alert", value=False)




