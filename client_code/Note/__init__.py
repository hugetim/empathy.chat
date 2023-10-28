from ._anvil_designer import NoteTemplate
class Note(NoteTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.link_1.popover(self.text, 
                        placement = 'top', 
                        trigger='manual',
                       )

  def link_1_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.link_1.pop('toggle')
