import anvil.users
import anvil.google.auth, anvil.google.drive, anvil.google.mail
from anvil.google.drive import app_files
import anvil.secrets
import anvil.email
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from . import groups
from . import server_misc as sm
from . import parameters as p


@sm.authenticated_callable
@anvil.tables.in_transaction
def serve_my_groups(port_my_groups, method, kwargs):
  print(f"groups_server: {method}({kwargs}) called on {port_my_groups}")
  my_groups = MyGroups(port_my_groups)
  my_groups.relay(method, kwargs)
  return my_groups.portable()


class MyGroups(groups.MyGroups): 
  def __init__(self, port_my_groups):
    self.update(port_my_groups)

  def portable(self):
    port = groups.MyGroups()
    port.update(self)
    return port  
    
  def relay(self, method, kwargs=None):
    if not kwargs:
      kwargs = {}
    return getattr(self, method)(**kwargs)
  
  def load(self, user_id=""):
    user = sm.get_user(user_id)
    rows = app_tables.groups.search(hosts=user)
    self.groups = []
    for row in rows:
      self.groups.append(groups_server.Group.from_group_row(row, portable=True))
