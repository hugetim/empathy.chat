from ._anvil_designer import InviteTemplate
from anvil import *
from ....glob import publisher


class Invite(InviteTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self._content = self.custom_1
    publisher.subscribe("invite", self, self.dispatch_handler)

  def _reset_and_load(self, component):
    self._content.remove_from_parent()
    self._content = component
    self.add_component(self._content)

  def go_invite_a(self, item):
    from .InviteA import InviteA
    self._reset_and_load(InviteA(item=item))
  
  def go_invite_b(self, item):
    from .InviteB import InviteB
    self._reset_and_load(InviteB(item=item))

  def go_invite_e(self, item):
    from .InviteE import InviteE
    self._reset_and_load(InviteE(item=item))
  
  def dispatch_handler(self, dispatch):
    if dispatch.title == "go_invite_b":
      self.go_invite_b(dispatch.content)
    elif dispatch.title == "success":
      self._close_alert(value="success")
    else:
      h.warning(f"Unhandled Invite dispatch: {dispatch}")

  def _close_alert(self, value):
    publisher.unsubscribe("invite", self)
    self.raise_event("x-close-alert", value=value)
    