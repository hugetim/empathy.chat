import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from . import helper as h
from . import parameters as p


@anvil.server.portable_class
class MyGroups(h.PortItem):
  repr_desc = "groups.MyGroups: "
  server_fn_name = 'serve_my_groups'
  def __init__(self, name="New Group", group_id=None, groups=None):
    self.name = name
    self.group_id = group_id
    self.groups = groups if groups else []

   
@anvil.server.portable_class
class MyGroup(h.PortItem):
  repr_desc = "groups.MyGroup: "
  server_fn_name = 'serve_my_group'
  def __init__(self, name="", group_id="", members=None, invites=None):
    self.name = name
    self.group_id = group_id
    self.members = members if members else []
    self.invites = invites if invites else []


@anvil.server.portable_class
class Invite(h.PortItem):
  repr_desc = "groups.Invite: "
  server_fn_name = 'serve_group_invite'
  def __init__(self, link_key="", invite_id="", expire_date=None, spec=None):
    self.link_key = link_key
    self.invite_id = invite_id
    self.expire_date = expire_date
    self.spec = spec
   
  @property
  def url(self):
    return f"{p.URL}#?group_invite={self.link_key}"
