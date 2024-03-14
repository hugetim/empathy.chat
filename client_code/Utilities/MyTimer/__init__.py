from ._anvil_designer import MyTimerTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files

GRAY300 = "#E0E0E0"
GRAY400 = "#BDBDBD"
GRAY500 = "#9E9E9E"
GRAY600 = "#757575"
GRAY700 = "#616161"
GRAY800 = "#424242"
GRAY900 = "#212121"

class MyTimer(MyTimerTemplate):
    def __init__(self, **properties):
        self._reset_value = 10*60
        self._total_seconds = self._reset_value
        self._paused = True
        self._enabled = False

        # Set Form properties and Data Bindings.
        self.init_components(**properties)

    @property
    def minutes(self):
        return (self._total_seconds % 3600)//60

    @property
    def seconds(self):
        return self._total_seconds % 60

    def update_time(self, total_seconds=None, update_reset_value=False):
        if total_seconds is not None:
            self._total_seconds = max(0, min(60*60-1, total_seconds))
            if self.minutes_text_box.foreground:
                self.minutes_text_box.foreground = self.time_color()
        if update_reset_value and self._total_seconds >= 1:
            self._reset_value = self._total_seconds
        elif update_reset_value:
            self.update_paused(True)
        self._update_button_status(update_reset_value)
        self.minutes_text_box.text = self.minutes
        self.seconds_text_box.text = f"{self.seconds:02d}"

    def _update_button_status(self, update_reset_value=False):
        if self._total_seconds >= 1:
            self.play_button.enabled = True
        if update_reset_value and self._total_seconds >= 1:
            if self.paused:
                self.reset_button.enabled = False
        else:
            if update_reset_value or self._total_seconds < 1:
                self.play_button.enabled = False
            if self.paused:
                self.reset_button.enabled = self._total_seconds != self._reset_value
            else:
                self.reset_button.enabled = True

    @property
    def paused(self):
        return self._paused

    @paused.setter
    def paused(self, value):
        self.update_paused(value)

    def update_paused(self, paused=None):
        if paused is not None:
            self._paused = paused
        if self._paused:
            self.play_button.icon = "fa:play"
            self.timer_1.interval = 0
        else:
            self.raise_event('started')
            self.play_button.icon = "fa:pause"
            self.timer_1.interval = 1
        self._update_button_status()
        input_enabled = self._paused and self._enabled
        for text_box in [self.minutes_text_box, self.seconds_text_box]:
            text_box.enabled = self._enabled
        self.minutes_text_box.foreground = "" if input_enabled else self.time_color()
        for comp in [self.seconds_text_box, self.label_1, self.play_button, self.reset_button]:
            comp.foreground = "" if input_enabled else GRAY300

    def _play_button_click(self, **event_args):
        """This method is called when the button is clicked"""
        self.update_paused(not self._paused)

    def _timer_1_tick(self, **event_args):
        """This method is called Every [interval] seconds. Does not trigger if [interval] is 0."""
        if self._total_seconds >= 1:
            self.update_time(self._total_seconds - 1)
            if self._total_seconds < 1:
                self.update_paused(True)
                self.raise_event('elapsed')

    def _minutes_text_box_lost_focus(self, **event_args):
        """This method is called when the TextBox loses focus"""
        self.minutes = self.minutes_text_box.text

    @minutes.setter
    def minutes(self, value):
        try:
            new_minutes = min(59, max(0, int(value)))
        except TypeError:
            new_minutes = self.minutes
        self.update_time(self._total_seconds + (new_minutes - self.minutes)*60, update_reset_value=True)

    def _seconds_text_box_lost_focus(self, **event_args):
        """This method is called when the TextBox loses focus"""
        self.seconds = self.seconds_text_box.text

    @seconds.setter
    def seconds(self, value):
        try:
            new_seconds = min(59, max(0, int(value)))
        except TypeError:
            new_seconds = self.seconds
        self.update_time(self._total_seconds + new_seconds - self.seconds, update_reset_value=True)

    @property
    def visible(self):
        return self.flow_panel_1.visible

    @visible.setter
    def visible(self, value):
        self.flow_panel_1.visible = value

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value
        self.play_button.visible = self._enabled
        self.reset_button.visible = self._enabled
        self.update_paused()

    @property
    def align(self):
        return self.flow_panel_1.align

    @align.setter
    def align(self, value):
        self.flow_panel_1.align = value

    @property
    def total_seconds(self):
        return self._total_seconds

    def start_countdown(self, total_seconds=None):
        if total_seconds is not None:
            self.update_time(total_seconds, update_reset_value=True)
        self.update_paused(False)

    def _text_box_focus(self, **event_args):
        """This method is called when the TextBox gets focus"""
        self.update_paused(True)

    def reset_button_click(self, **event_args):
        """This method is called when the button is clicked"""
        self.update_time(self._reset_value)

    def time_color(self):
        seconds_left = self._total_seconds
        if seconds_left >= 2*60:
            return GRAY300
        elif seconds_left >= 1*60:
            return GRAY400
        else:
            return GRAY500
