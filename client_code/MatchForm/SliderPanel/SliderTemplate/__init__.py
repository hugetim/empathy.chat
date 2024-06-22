from ._anvil_designer import SliderTemplateTemplate
from anvil import *

class SliderTemplate(SliderTemplateTemplate):
    def __init__(self, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)

        # Any code you write here will run before the form opens.
        self.their_name = ""
        if self.item.get('name'):
            self.update_name(self.item.get('name'))

    def update_name(self, their_name):
        self.their_name = their_name
        self.their_label.text = f"{their_name}:"

