from ._anvil_designer import PhoneTemplate
from anvil import *
import anvil.users
import anvil.server
from ... import helper as h
from ... import ui_procedures as ui
from anvil_extras.utils import auto_refreshing, wait_for_writeback


class Phone(PhoneTemplate):
  item_keys = {"phone"} 
  #status in {None, "editing", "confirming", "confirmed"}
  
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.update("confirmed" if self.item['phone'] else None)
  
  def update(self, status=None):
    self.phone_text_box.enabled = True
    self.phone_button.visible = True
    self.phone_button.enabled = False
    self.phone_instructions_label.visible = False
    self.phone_code_panel.visible = False
    self.phone_error_label.visible = False
    if status:
      if status == "editing":
        self.phone_button.enabled = True
      elif status == "confirming":
        self.phone_text_box.enabled = False
        self.phone_instructions_label.visible = True
        self.phone_code_panel.visible = True
      elif status == "confirmed":
        self.phone_text_box.enabled = False
        self.phone_button.visible = False
      else:
        print("Warning: unknown Phone status")
  
  def phone_text_box_change(self, **event_args):
    self.phone_button.enabled = bool(self.phone_text_box.text)
      
  def phone_button_click(self, **event_args):
    raw = self.phone_text_box.text
    subscriber = "".join(c for c in raw if c.isdigit())
    if len(subscriber) == 10:
      number = "+1" + subscriber
      self.phone_text_box.text = self._format_subscriber(subscriber)
      out = anvil.server.call('send_verification_sms', number)
      if out == "code sent":
        self.phone_instructions_label.text = (
          f"A text message has been sent to {number}. "
          "Please enter the verification code it contains."
        )
        self.update("confirming")
        self.phone_code_text_box.focus()
      elif out == "number unavailable":
        message = ("That number is already confirmed by another account, "
                   "and it cannot be used for a separate account.")
        self.phone_error_label.text = message
        self.phone_error_label.visible = True
      else:
        print("Warning: unhandled 'send_verification_sms' return value")
    else:
      if len(subscriber) > 10:
        message = "The number entered has too many digits."
      else:
        message = "The number entered has too few digits."
      self.phone_error_label.text = message
      self.phone_error_label.visible = True

  def _format_subscriber(self, number):
    if len(number) != 10:
      print("Warning: not 10 subscriber number digits")
    return f"({number[:3]}){number[3:6]}-{number[6:10]}"
    
  def phone_code_text_box_change(self, **event_args):
    self.phone_code_submit_button.enabled = bool(self.phone_code_text_box.text)

  def phone_code_submit_button_click(self, **event_args):
    code_matches = anvil.server.call('check_phone_code', 
                                     self.phone_code_text_box.text,
                                    )
    if code_matches:
      alert("Phone number verification successful.")
      self.update("confirmed")
      ui.reload()
    else:
      self.phone_error_label.text = "The code submitted does not match (or is expired)."
      self.phone_error_label.visible = True

  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.update("editing")



