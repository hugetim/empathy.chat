from ._anvil_designer import PhoneTemplate
from anvil import *
import anvil.server
from ... import helper as h


class Phone(PhoneTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

  def phone_text_box_change(self, **event_args):
    self.phone_button.enabled = self.phone_text_box.text
      
  def phone_button_click(self, **event_args):
    self.phone_button.enabled = False
    raw = self.phone_text_box.text
    number = "+1" + "".join(c for c in raw if c.isdigit())
    assert len(number) == 12 # including "+1"
    anvil.server.call('send_verification_sms', number)
    self.phone_instructions_label.text = (
      f"A text message has been sent to {number} "
      "Please enter the verification code it contains."
    )
    self.phone_instructions_label.visible = True
    self.phone_code_panel.visible = True
    self.phone_code_text_box.focus()

  def phone_code_text_box_change(self, **event_args):
    self.phone_code_submit_button.enabled = self.phone_code_text_box.text

  def phone_code_submit_button_click(self, **event_args):
    code_matches = anvil.server.call('check_phone_code', 
                                     self.phone_code_text_box.text,
                                    )
    print(code_matches)
    

