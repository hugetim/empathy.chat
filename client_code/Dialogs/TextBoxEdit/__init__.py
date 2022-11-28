from ._anvil_designer import TextBoxEditTemplate
from anvil import *


class TextBoxEdit(TextBoxEditTemplate):
  item_keys = {'text', 'disallowed_list'}

  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    self._original_text = self.item['text']

  def text_box_change(self, **event_args):
    self.item['text'] = self.text_box.text.strip()
    self.save_button.enabled = self.item['text'] and self.item['text'] != self._original_text
    self.error_label.visible = False

  def save_button_click(self, **event_args):
    if self.save_button.enabled:
      if self.item['text'] not in self.item['disallowed_list']:
        self.raise_event("x-close-alert", value=True)
      else:
        self.error_label.text = "That name is already taken (or otherwise not allowed)."
        self.error_label.visible = True

  def cancel_button_click(self, **event_args):
    self.raise_event("x-close-alert", value=False)
