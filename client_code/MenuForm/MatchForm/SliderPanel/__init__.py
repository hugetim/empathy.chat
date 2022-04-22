from ._anvil_designer import SliderPanelTemplate
from anvil import *
import anvil.users
import anvil.server
from .... import exchange_controller as ec
from .... import helper as h


class SliderPanel(SliderPanelTemplate):
  def __init__(self, **properties):
    """self.item assumed to have these keys: 
    'visible',
    'their_value', default 5
    'my_value', default 5
    'status' in [None, 'submitted', 'received', 'waiting']
    """
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.their_name = ""
    if self.item.get('their_name'):
      self.update_name(self.item.get('their_name'))
    self.update_status()

  def update_status(self, new_status="not provided"):
    if new_status != "not provided":
      self.item['status'] = new_status
    if self.item['status'] in [None, 'waiting']:
      self.title_label.text = 'How full is your "empathy tank"? (Empty: angry/distant, Full: content/open)'                              
      self.title_label.bold = True
      self.left_column_panel.tooltip = ("After you both submit, you can compare positions to help you decide who gives empathy first. "
                                        "More full usually means it's easier to be curious about what the other is feeling and needing.")
    elif self.item['status'] == 'submitted':
      self.title_label.text = 'Status: Submitted, waiting for other to submit... (Empty: angry/distant, Full: content/open)'                              
      self.title_label.bold = False
      self.left_column_panel.tooltip = ("After you both submit, you can compare positions to help you decide who gives empathy first. "
                                        "More full usually means it's easier to be curious about what the other is feeling and needing.")
    elif self.item['status'] == 'received':
      self.title_label.text = 'You can compare to help decide who gives empathy first (Empty: angry/distant, Full: content/open)'
      self.title_label.bold = True
      self.left_column_panel.tooltip = ('It may be that neither of you is "full" enough to feel willing/able to give empathy first. '
                                        'If so, consider cancelling or rescheduling.')
    else:
      h.warning(f"Unexpected SliderPanel status: {self.item['status']}")
      self.title_label.text = ("More full usually means it's easier to be curious about what the other is feeling and needing. "
                               '(Empty: angry/distant, Full: content/open)')
      self.title_label.bold = False
    self.refresh_data_bindings()
      
  def update_name(self, their_name):
    self.their_name = their_name
    self.their_label.text = f"{their_name}:"
      
  def hide_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.raise_event('x-hide')
#     self.item['visible'] = False
#     self.update_status()

  def submit_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.item['status'] = "submitted"
    self.update_status()
    their_value = ec.ExchangeState.submit_slider(self.my_slider.value)
    if type(their_value) != str:
      self.receive_value(their_value)

  def receive_value(self, their_value):
    self.item['their_value'] = their_value
    self.item['status'] = "received"
    self.update_status()
    self.their_slider.scroll_into_view()
      
  def show_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.item['visible'] = True
    self.update_status()

