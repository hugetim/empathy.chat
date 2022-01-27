import anvil.server
import anvil.users
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


@anvil.server.portable_class 
class MyRequest(h.PortItem, h.AttributeToKey):
  pass