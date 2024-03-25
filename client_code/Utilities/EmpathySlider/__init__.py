from ._anvil_designer import EmpathySliderTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files

class EmpathySlider(EmpathySliderTemplate):
    # Reuse standard properties from Anvil
    visible = HtmlTemplate.visible
    tag = HtmlTemplate.tag    
    
    def __init__(self, **properties):
        self._labels = []
        
        # Set Form properties and Data Bindings.        
        self.init_components(**properties)

    @property
    def enabled(self):
        return self.slider_1.enabled
        
    @enabled.setter
    def enabled(self, v):
        self.slider_1.enabled = v
        
    @property
    def value(self):
        return self.slider_1.value
        
    @value.setter
    def value(self, v):
        self.slider_1.value = v
        
    @property
    def minval(self):
        return self.slider_1.min
        
    @minval.setter
    def minval(self, v):
        self.slider_1.min = v
        
    @property
    def maxval(self):
        return self.slider_1.max
        
    @maxval.setter
    def maxval(self, v):
        self.slider_1.max = v
        
    @property
    def step(self):
        return self.slider_1.step
        
    @step.setter
    def step(self, v):
        self.slider_1.step = v
        # Reset the formatter since changing the step value can change
        # where the labels hit on the slider
        self.set_slider_formatter()
        
    @property
    def labels(self):
        return self._labels
        
    @labels.setter
    def labels(self, v):
        if v and type(v) != list:
            raise ValueError(f"Setting slider labels should use a list, not {type(v)}")

        self._labels = v
        self.set_slider_formatter()

    def slider_1_change(self, handle, **event_args):
        self.raise_event('change')
        
    def set_slider_formatter(self):
        # The number of labels becomes the number of pips in the slider
        if not self.labels:
            self.slider_1.pips = False
            return
            
        self.slider_1.pips = True
        self.slider_1.pips_values = len(self.labels)

        # Each label gets evenly distributed along the range of the slider,
        # the first at the minval, the last at the maxval, and the rest
        # in between.  If there is only one label it's put in the middle.
        if len(self.labels) == 1:
            num_to_desc = {(self.minval+self.maxval)/2 : self.labels[0]}
        else:
            num_to_desc = {self.minval: self.labels[0], self.maxval: self.labels[-1]}

            increment = (self.minval+self.maxval)/(len(self.labels)-1)
            start = increment
            for i in range(1, len(self.labels) - 1):
                # Make sure the label spot is on a step increment
                temp = start - (start % self.step)
                num_to_desc[temp] = self.labels[i]
                start += increment

        # The rest of this comes straight from the Anvil Extras demo
        desc_to_num = {v: k for k, v in num_to_desc.items()}

        self.slider_1.format = {
            # to should return a str
            "to": lambda num: num_to_desc.get(num, str(num)),
            # from should return a number - if it fails then an attempt will be made to convert the str to float
            "from": lambda desc: desc_to_num[desc],
        }

        ### it's also possible to provide a custom formatter to tooltips - only to is required
        self.slider_1.tooltips = {"to": lambda num: format(num, ".0f")}
        
