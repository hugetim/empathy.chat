from ._anvil_designer import InvitedTemplate
from anvil import *
from ...glob import publisher
from ... import helper as h


class Invited(InvitedTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self._content = self.spacer_1
    publisher.subscribe("invited", self, self.dispatch_handler)
    self.go_invited1(self.item)

  def _reset_and_load(self, component):
    self._content.remove_from_parent()
    self._content = component
    self.add_component(self._content)
    
  def go_invited2(self, item):
    from .Invited2 import Invited2
    self._reset_and_load(Invited2(item=item))
    
  def go_invited1(self, item):
    from .Invited1 import Invited1
    self._reset_and_load(Invited1(item=item))

  def dispatch_handler(self, dispatch):
    if dispatch.title == "go_invited1":
      self.go_invited1(dispatch.content)
    elif dispatch.title == "go_invited2":
      self.go_invited2(dispatch.content)
    elif dispatch.title == "success":
      self._close_alert(value=True)
    elif dispatch.title == "failure":
      self._close_alert(value=False)
    else:
      h.warning(f"Unhandled Invited dispatch: {dispatch}")

  def _close_alert(self, value):
    publisher.unsubscribe("invited", self)
    self.raise_event("x-close-alert", value=value)
