from ._anvil_designer import SliderPanelTemplate
from anvil import *
from ... import exchange_controller as ec
from ... import helper as h


class SliderPanel(SliderPanelTemplate):
    def __init__(self, **properties):
        """self.item assumed to have these keys:
        'them',
        'my_value', default 5
        'status' in [None, 'submitted', 'received', 'waiting']
        """

        # Set up the Anvil Extras slider for custom labels
        self.set_slider_formatter()
        
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
        if not ec.any_slider_values_missing(them):
            self.item['status'] = "received"
            self.update_status()
            self.them_repeating_panel.scroll_into_view()

    def set_slider_formatter(self):
        num_to_desc = {
            0: "Empty",
            5: "",
            10: "Full",
        }

        self.slider_1.pips = True
        self.slider_1.pips_values = len(num_to_desc)
        
        desc_to_num = {v: k for k, v in num_to_desc.items()}

        self.slider_1.format = {
            # to should return a str
            "to": lambda num: num_to_desc.get(num, str(num)),
            # from should return a number - if it fails then an attempt will be made to convert the str to float
            "from": lambda desc: desc_to_num[desc],
        }

        # ### it's also possible to provide a custom formatter to tooltips - only to is required
        # self.slider_1.tooltips = {"to": lambda num: format(num, ".0f")}
