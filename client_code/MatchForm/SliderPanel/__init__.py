from ._anvil_designer import SliderPanelTemplate
from anvil import *
from ... import exchange_controller as ec
from ... import helper as h


class SliderPanel(SliderPanelTemplate):
  def __init__(self, **properties):
    """self.item assumed to have these keys: 
    'their_value', default 5
    'my_value', default 5
    'status' in [None, 'submitted', 'received', 'waiting']
    """
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    them = self.item.get('them')
    if them:
      self.them_repeating_panel.items = them
    self.update_status()

  def update_status(self, new_status="not provided"):
    if new_status != "not provided":
      self.item['status'] = new_status
    if self.item['status'] in [None, 'waiting']:
      self.title_label.text = 'How full is your "empathy tank"? (Empty: distant/upset, Full: content/open)'                              
      self.title_label.bold = True
      self.left_column_panel.tooltip = ("Once each of you submits, you can compare positions to help decide who receives empathy first. "
                                        "More full usually means it's easier to be curious about what another is feeling and needing.")
    elif self.item['status'] == 'submitted':
      self.title_label.text = 'Status: Submitted, waiting for other to submit... (Empty: distant/upset, Full: content/open)'                              
      self.title_label.bold = False
      self.left_column_panel.tooltip = ("Once each of you submits, you can compare positions to help decide who receives empathy first. "
                                        "More full usually means it's easier to be curious about what another is feeling and needing.")
    elif self.item['status'] == 'received':
      self.title_label.text = 'You can compare to help decide who receives empathy first (Empty: distant/upset, Full: content/open)'
      self.title_label.bold = True
      self.left_column_panel.tooltip = ('It may be that no one is "full" enough to feel willing/able to give empathy first. '
                                        'If so, consider cancelling or rescheduling.')
    else:
      h.warning(f"Unexpected SliderPanel status: {self.item['status']}")
      self.title_label.text = ("More full usually means it's easier to be curious about what the other is feeling and needing. "
                               '(Empty: angry/distant, Full: content/open)')
      self.title_label.bold = False
    self.refresh_data_bindings()
      
  def hide_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.raise_event('x-hide')

  def submit_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.item['status'] = "submitted"
    self.update_status()
    them = ec.submit_slider(self.my_slider.value)

  def receive_them(self, them):
    self.them_repeating_panel.items = them
    if not any([ec.slider_value_missing(o_dict['slider_value']) for o_dict in them]):
      self.item['status'] = "received"
      self.update_status()
      self.them_repeating_panel.scroll_into_view()
