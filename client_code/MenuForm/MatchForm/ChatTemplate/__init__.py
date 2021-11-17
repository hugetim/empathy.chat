from ._anvil_designer import ChatTemplateTemplate
from anvil import *
import anvil.users
import anvil.server


class ChatTemplate(ChatTemplateTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    _datetime = self.item.get('time_stamp')
    if _datetime:
      self.meta_label.text = _datetime.strftime("%I:%M%p")
      self.day_label.text = _datetime.strftime("%A, %b %d, %Y")
    else:
      self.meta_label.visible = False
      
    if self.item.get('new_day'):
      self.day_label.visible = True
    else:
      self.horizontal_rule_1.remove_from_parent()