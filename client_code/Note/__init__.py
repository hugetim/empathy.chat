from ._anvil_designer import NoteTemplate
from anvil_extras import popover


class Note(NoteTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.


  @property
  def text(self):
    return self._text
  
  @text.setter
  def text(self, value):
    self._text = value
    if self._text:
      self.button_1.popover(self._text,
                          placement = 'top', 
                          trigger='manual',
                         )
      self.button_1.visible = True
  
  def button_1_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.button_1.pop('toggle')
