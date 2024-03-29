from ._anvil_designer import ChatTemplateTemplate
from anvil import *
from ... import helper as h


class ChatTemplate(ChatTemplateTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.meta_label.text = self.item.get("label", "")
    _datetime = self.item.get('time_stamp')
    if _datetime:
      if self.meta_label.text:
        self.meta_label.text += " "
      self.meta_label.text += h.time_str(h.as_local_tz(_datetime))
      self.day_label.text = h.dow_date_str(h.as_local_tz(_datetime))
    self.meta_label.visible = bool(self.meta_label.text)
    if self.item.get('new_day'):
      self.day_label.visible = True
    else:
      self.horizontal_rule_1.remove_from_parent()