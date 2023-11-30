from ._anvil_designer import CreateFormTemplate
from anvil import *
from .... import helper as h
from .... import portable as t
from .... import glob
from datetime import timedelta
from .Eligibility import Eligibility


class CreateForm(CreateFormTemplate):
  def proposal(self):
    """Convert self.item into a proposal dictionary"""
    eligibility = {key: self.eligibility_form.item[key] 
                   for key in self.eligibility_form.export_item_keys}
    self.item.update(eligibility)
    return t.Proposal.from_create_form(self.item)

  def proptime(self):
    return t.ProposalTime.from_create_form(self.item)
  
  def __init__(self, item, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(item=item, **properties)
    
    # Any code you write here will run when the form opens.
    if self.item['now_allowed']:
      self.now_radio_button.selected = self.item['start_now']
      self.later_radio_button.selected = not self.item['start_now']
    else:
      self.item['start_now'] = False
      self.now_radio_button.visible = False
      self.later_radio_button.visible = False
    self.start_label.spacing_below = "small"
    self.date_picker_start.spacing_above = "small"
    self.drop_down_duration.items = list(zip(t.DURATION_TEXT.values(), t.DURATION_TEXT.keys()))
    self.drop_down_cancel.items = list(zip(t.CANCEL_TEXT.values(), t.CANCEL_TEXT.keys()))
    self.normalize_initial_state()
    self.date_picker_start_initialized = False
    self.date_picker_cancel_initialized = False
    self.update()
    self.eligibility_form = Eligibility(item=item)
    self.eligibility_linear_panel.add_component(self.eligibility_form)
    self.eligible_label.visible = self.eligibility_form.any_visible()
    if self.item['note'] or self.item['cancel_buffer'] != 15:
      self.reveal_advanced()
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
    if self.item['alt']:
      self.now_radio_button.enabled = False
      self.now_radio_button.foreground = "theme:Gray 600"
      self.now_radio_button.tooltip = 'To switch to "Now", first remove the Alternate Times'
    else:
      self.now_radio_button.enabled = True
      self.now_radio_button.foreground = "theme:Black"
      self.now_radio_button.tooltip = ''
    if self.item['start_now']:
      self.save_button.text = "START"
      self.save_button.icon = "fa:child"
      self.date_picker_start.visible = False
      self.button_add_alternate.visible = False
      self.alternate_spacer.visible = False
      if not self.item['alt']:
        self.column_panel_cancel.visible = False
      else:
        # this keeps the "Cancel" column heading for the alternatives
        h.warning(f"alts should no longer be allowed for start_now")
        #self.column_panel_cancel.visible = True
        self.drop_down_cancel.visible = False
        self.date_picker_cancel.visible = False      
    else: # Later...
      self.now_label.visible = False
      self.save_button.text = "SAVE"
      self.save_button.icon = ""
      if not self.date_picker_start_initialized:
        self.init_date_picker_start()
      self.date_picker_start.visible = True
      self.button_add_alternate.visible = len(self.item['alt']) < t.MAX_ALT_TIMES
      #self.column_panel_cancel.visible = True
      self.drop_down_cancel.visible = True
      if self.item['cancel_buffer'] == "custom":
        if not self.date_picker_cancel_initialized:
          self.init_date_picker_cancel()
        self.date_picker_cancel.visible = True
      else:
        self.date_picker_cancel.visible = False
    self.check_times()
    self.refresh_data_bindings()
    
  def update(self):
    self.update_times()
    self.update_size()
    
  def update_size(self):
    new_items = [
      ("pair/dyad (1 other participant)", (2, 2)),
      ("triad (2 other participants)", (3, 3)),
    ]
    if not self.item['start_now']:
      new_items.append(("pair or triad (1 or 2 others, however many accept in time)", (2, 3)))
    elif self.item['min_size'] != self.item['max_size']:
      self.item['min_size'] = self.item['max_size']
    self.size_drop_down.items = new_items

  def radio_start_change(self, **event_args):
    """This method is called when an item is selected"""
    sender = event_args.get('sender')
    if sender:
      self.item['start_now'] = bool(int(sender.get_group_value()))
    self.update_times()

  def drop_down_cancel_change(self, **event_args):
    """This method is called when an item is selected"""
    if self.item['alt']:
      for alt_item in self.item['alt']:
        alt_item['cancel_buffer'] = self.item['cancel_buffer']
      for time_component in self.repeating_panel_1.get_components():
        time_component.update()
    self.update()
    
  def date_picker_start_change(self, **event_args):
    """This method is called when the selected date changes"""
    self.update()

  def date_picker_cancel_change(self, **event_args):
    """This method is called when the selected date changes"""
    if self.item['alt']:
      for alt_item in self.item['alt']:
        alt_item['cancel_date'] = self.item['cancel_date']
      for time_component in self.repeating_panel_1.get_components():
        time_component.update()
    self.update()    

  def drop_down_duration_change(self, **event_args):
    """This method is called when an item is selected"""
    if self.item['alt']:
      for alt_item in self.item['alt']:
        alt_item['duration'] = self.item['duration']
      for time_component in self.repeating_panel_1.get_components():
        time_component.check_times()
    self.check_times()
  
  def check_times(self):
    self.label_start.visible = False
    self.label_cancel.visible = False
    messages = self.proptime().get_errors(self.item['conflict_checks'])
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
      self.update_save_enable()    
      
  def update_save_enable(self):
    enabled = all([self.item['save_ready']]
                   + [item['save_ready'] for item in self.item['alt']])
    if not enabled and not self.item['start_now']:
      self.reveal_advanced()
    self.save_button.enabled = enabled
    
  def button_add_alternate_click(self, **event_args):
    """This method is called when the button is clicked"""
    if not self.item['alt']:
      start_1 = h.now() if self.item['start_now'] else self.item['start_date']
      if self.item['cancel_buffer'] == 0:
        cancel_buffer = t.CANCEL_DEFAULT_MINUTES
      else:
        cancel_buffer = self.item['cancel_buffer']
      self.item['alt'] = [{'start_date': (start_1 + t.DEFAULT_NEXT_DELTA),
                           'duration': self.item['duration'],
                           'cancel_buffer': cancel_buffer,
                           'cancel_date': self.item.get('cancel_date'),
                           'time_id': None,
                           'conflict_checks': self.item['conflict_checks'],
                           'save_ready': True,
                          }]
    else:
      previous_item = self.item['alt'][-1]
      self.item['alt'] += [{'start_date': (previous_item['start_date']
                                           + t.DEFAULT_NEXT_DELTA),
                            'duration': previous_item['duration'],
                            'cancel_buffer': previous_item['cancel_buffer'],
                            'cancel_date': previous_item.get('cancel_date'),
                            'time_id': None,
                            'conflict_checks': self.item['conflict_checks'],
                            'save_ready': True,
                           }]
    self.update()
      
  def remove_alternate(self, item_to_remove, **event_args):
    self.item['alt'].remove(item_to_remove)
    self.update()

  def save_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    glob.default_request.update(self.proposal().get_default_request_update())
    self.raise_event("x-close-alert", value=True)

  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.raise_event("x-close-alert", value=False)

  def advanced_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.reveal_advanced()

  def reveal_advanced(self):
    self.column_panel_cancel.visible = not self.item['start_now']
    self.note_flow_panel.visible = True
    self.advanced_link.visible = False
