from ._anvil_designer import SettingsFormTemplate
from anvil import *
import anvil.users
import anvil.server
from ... import helper as h
from .Phone import Phone


class SettingsForm(SettingsFormTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    
    phone, p_sms, m_sms = anvil.server.call('get_settings') #re, re_opts, re_st, 
    #self.init_request_em_opts(re, re_opts, re_st)
    self.timer_2.interval = 0 #5
    self.phone_form = Phone(item={"phone": phone[2:] if phone else "", # removing "+1" 
                                 })
    self.phone_panel.add_component(self.phone_form)
    self.notifications_panel.visible = bool(phone)
    self.pinged_drop_down.items += [("SMS (default)", "sms"),  
                                    ("email", "email"),
                                   ]
    self.message_drop_down.items += [("SMS", "sms"),
                                     ("email (default)", "email"),
                                     ("don't notify", None),
                                    ]
    self.specific_request_drop_down.items += [("SMS", "sms"),
                                 ("email (default)", "email"),
                                 ("don't notify", None),
                                ]
    self.pinged_sms_switch.checked = p_sms
    self.message_sms_switch.checked = m_sms
    
  def form_show(self, **event_args):
    """This method is called when the HTML panel is shown on the screen"""
    self.top_form = get_open_form()

  def pinged_sms_switch_change(self, **event_args):
    """This method is called when this switch is checked or unchecked"""
    anvil.server.call('set_pinged_sms', self.pinged_sms_switch.checked) 

  def message_sms_switch_change(self, **event_args):
    """This method is called when this switch is checked or unchecked"""
    anvil.server.call('set_message_sms', self.pinged_sms_switch.checked)
  
    
  def request_em_check_box_change(self, **event_args):
    """This method is called when this checkbox is checked or unchecked"""
    checked = self.request_em_check_box.checked
    self.set_request_em_options(checked)
    re_st = anvil.server.call('set_request_em', checked)
    self.request_em_set_time = re_st

  def set_request_em_options(self, checked):
    """Update request_em options visibility/enabled."""
    if checked:
      self.re_radio_button_panel.visible = True
      self.re_radio_button_indef.enabled = True
      self.re_radio_button_fixed.enabled = True
      self.text_box_hours.enabled = self.re_radio_button_fixed.selected
    else:
      self.re_radio_button_panel.visible = False
      self.re_radio_button_indef.enabled = False
      self.re_radio_button_fixed.enabled = False
      self.text_box_hours.enabled = False

  def init_request_em_opts(self, re, re_opts, re_st):
    """Initialize to saved request_em option values"""
    self.pause_hours_update = True
    self.request_em_check_box.checked = re
    self.request_em_hours = re_opts["hours"]
    self.request_em_set_time = re_st
    fixed = bool(re_opts["fixed"])
    self.re_radio_button_indef.selected = not fixed
    self.re_radio_button_fixed.selected = fixed
    if self.request_em_check_box.checked and fixed:
      hours_left = h.re_hours(self.request_em_hours, 
                              self.request_em_set_time)
    else:
      hours_left = self.request_em_hours
    self.set_request_em_options(re)
    self.text_box_hours.text = "{:.1f}".format(hours_left)
    self.pause_hours_update = False

  def re_radio_button_indef_clicked(self, **event_args):
    fixed = False
    self.text_box_hours.enabled = fixed
    hours = self.text_box_hours.text
    self.request_em_hours = hours
    re_st = anvil.server.call('set_request_em_opts', fixed, hours)
    self.request_em_set_time = re_st
    
  def re_radio_button_fixed_clicked(self, **event_args):
    fixed = True
    self.text_box_hours.enabled = fixed
    hours = self.text_box_hours.text
    self.request_em_hours = hours
    re_st = anvil.server.call('set_request_em_opts', fixed, hours)
    self.request_em_set_time = re_st

  def text_box_hours_pressed_enter(self, **event_args):
    self.update_hours()

  def text_box_hours_lost_focus(self, **event_args):
    self.update_hours()
    self.pause_hours_update = False
  
  def update_hours(self):
    hours = self.text_box_hours.text
    if hours and hours > 0:
      fixed = self.re_radio_button_fixed.selected
      self.request_em_hours = hours
      re_st = anvil.server.call('set_request_em_opts', fixed, hours)
      self.request_em_set_time = re_st
    else:
      hours_left = h.re_hours(self.request_em_hours, 
                              self.request_em_set_time)
      self.text_box_hours.text = "{:.1f}".format(hours_left)

  def text_box_hours_focus(self, **event_args):
    self.pause_hours_update = True
    
  def timer_2_tick(self, **event_args):
    """This method is called approx. once per 5 seconds"""
    if (self.request_em_check_box.checked and self.re_radio_button_fixed.selected
        and self.pause_hours_update == False):
      hours_left = h.re_hours(self.request_em_hours, 
                              self.request_em_set_time)
      if hours_left <= 0:
        checked = False
        self.request_em_check_box.checked = checked
        self.set_request_em_options(checked)
        self.text_box_hours.text = "{:.1f}".format(self.request_em_hours)
        re_st = anvil.server.call_s('set_request_em', checked)
        self.request_em_set_time = re_st
      else:
        self.text_box_hours.text = "{:.1f}".format(hours_left)
