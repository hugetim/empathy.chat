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
    CANCEL_TEXT = {5: "5 min. prior",
                   15: "15 min. prior",
                   30: "30 min. prior",
                   60: "1 hr. prior",
                   120: "2 hrs. prior",
                   8*60: "8 hrs. prior",
                   24*60: "24 hrs. prior",
                   48*60: "48 hrs. prior",
                   "custom": "Custom Time",
                  }
    self.drop_down_cancel_1.items = [(CANCEL_TEXT[m], m)
                                     for m in (5, 15, 30, 60, 120, 8*60, 24*60, 48*60)]
    self.drop_down_cancel_1.items += [(CANCEL_TEXT["custom"],"custom")]
    self.drop_down_cancel_1.selected_value = 30
    self.drop_down_eligible.items = [("Allow anyone to accept (up to 3rd degree connections)", 3),
                                     ("Limit to 2nd degree connections (or closer)", 2),
                                     ("Limit to 1st degree connections", 1)]
    self.date_picker_start_1.date = (h.now() 
                                     + datetime.timedelta(seconds=60*p.MIN_NEXT_TIME))
    self.date_picker_start_1.min_date = h.now() + datetime.timedelta(seconds=60*5)
    

  def drop_down_start_change(self, **event_args):
    """This method is called when an item is selected"""
    if self.drop_down_start.selected_value == "now":
      self.column_panel_cancel_1.visible = False
      self.date_picker_start_1.visible = False
    else:
      self.column_panel_cancel_1.visible = True
      self.date_picker_start_1.visible = True

  def drop_down_cancel_1_change(self, **event_args):
    """This method is called when an item is selected"""
    if self.drop_down_cancel_1.selected_value == "custom":
      self.date_picker_cancel_1.visible = True
    else:
      self.date_picker_cancel_1.visible = False

  def date_picker_start_1_change(self, **event_args):
    """This method is called when the selected date changes"""
    if self.drop_down_cancel_1.selected_value == "custom":
      cancel_date = self.date_picker_cancel_1.date
    else:
      minutes_prior = self.drop_down_cancel_1.selected_value
      cancel_date = self.date_picker_start_1.date - datetime.timedelta(seconds=60*minutes_prior)
    if cancel_date < h.now():
      self.label_cancel_1.text = "Cancel time already past"








