from ._anvil_designer import SettingsFormTemplate
from anvil import *
import anvil.users
import anvil.server
from ... import helper as h
from ... import portable as port
from ... import glob
from .Phone import Phone
from ..DashForm.CreateForm.Eligibility import Eligibility


class SettingsForm(SettingsFormTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    
    lazy_items = [glob.user_items, glob.group_items, glob.starred_name_list] if glob.lazy_loaded else []
    phone, time_zone, notif_settings, self.elig_items = anvil.server.call('get_settings', lazy_items)
    #self.init_request_em_opts(re, re_opts, re_st)
    self.phone_form = Phone(item={"phone": phone[2:] if phone else "", # removing "+1" 
                                 })
    self.phone_panel.add_component(self.phone_form)
    self.essential_drop_down.items = [("text/SMS (default)", "sms"),
                                      ("email", "email"),
                                     ]
    self.essential_drop_down.selected_value = notif_settings.get('essential')
    self.message_drop_down.items = [("text/SMS", "sms"),
                                    ("email (default)", "email"),
                                    ("don't notify", None),
                                   ]
    if not phone: #order of these lines relative to those above and below matters
      self.essential_flow_panel.visible = False
      self.specific_flow_panel.visible = False
      self.sms_panel.visible = False
      self.email_label.text = "Email me regarding empathy requests from: "
      self.message_drop_down.items = self.message_drop_down.items[1:3]
    self.message_drop_down.selected_value = notif_settings.get('message')
    self.specific_drop_down.items = self.message_drop_down.items
    self.specific_drop_down.selected_value = notif_settings['specific'] if notif_settings.get('specific') else "email"
    self.update_eligibility_descs()
    self.time_zone_label.text = str(time_zone)
    
  def update_eligibility_descs(self):
    pseudo_props = {}
    for medium in ['sms', 'email']:
      pseudo_props[medium] = port.Proposal(**{k: self.elig_items[medium][k] for k in Eligibility.export_item_keys})
    self.sms_desc_label.text = pseudo_props['sms'].eligibility_desc
    self.email_desc_label.text = pseudo_props['email'].eligibility_desc 
    
  def form_show(self, **event_args):
    """This method is called when the HTML panel is shown on the screen"""
    self.top_form = get_open_form()

  def set_notif_settings(self, **event_args):
    notif_settings = {}
    for notif_type in ['essential', 'message', 'specific']:
      drop_down = getattr(self, notif_type + "_drop_down")
      notif_settings[notif_type] = drop_down.selected_value
    anvil.server.call('set_notif_settings', notif_settings, self.elig_items)

  def edit_eligibility_desc(self, medium):
    self.eligibility_form = Eligibility(item=dict(self.elig_items[medium]))
    medium_title = medium if medium == "email" else "text/SMS"
    result = alert(self.eligibility_form, large=True, title=f"Notify me by {medium_title} for requests from:", buttons=[("OK", True), ("Cancel", False)])
    if result:
      self.elig_items[medium] = self.eligibility_form.item
      self.update_eligibility_descs()
      self.set_notif_settings()
 
  def sms_edit_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.edit_eligibility_desc('sms')
    
  def email_edit_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.edit_eligibility_desc('email')
