from ._anvil_designer import RelationshipTemplate
from anvil import *


class Relationship(RelationshipTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    if self.item['child']:
      self.child_column_panel.add_component(Relationship(item=self.item['child']))
