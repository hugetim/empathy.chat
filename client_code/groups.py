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
  
  def __init__(self, groups=None, names_taken=None):
    self._groups = list(groups) if groups else []
    self.names_taken = names_taken if names_taken else []

  def __getitem__(self, position):
    return self._groups[position]
  
  def __len__(self):
    return len(self._groups)
  
   
@anvil.server.portable_class
class MyGroup(h.PortItem, h.AttributeToKey):
  repr_desc = "groups.MyGroup: "
  server_fn_name = 'serve_my_group'
  default_name = "New Group"
  
  def __init__(self, name="", group_id="", members=None, invites=None):
    self.name = name
    self.group_id = group_id
    self.members = members if members else []
    self.invites = invites if invites else []


@anvil.server.portable_class
class Invite(h.PortItem, h.AttributeToKey):
  repr_desc = "groups.Invite: "
  server_fn_name = 'serve_group_invite'
  def __init__(self, link_key="", invite_id="", expire_date=None, spec=None):
    self.link_key = link_key
    self.invite_id = invite_id
    self.expire_date = expire_date
    self.spec = spec
   
  @property
  def url(self):
    return f"{p.URL}#?group={self.link_key}"
  
  @property
  def expire_date_str(self):
    return h.short_date_str(self.expire_date)

  
def handle_link(link_key):
  print(f"groups.handle_link: {link_key}")
  user = anvil.users.get_user()
  invite = Invite(link_key=link_key)
  errors = invite.relay('visit', {'user': user})
  if not errors:
    from .Dialogs.Invited import Invited
    invited_alert = Invited(item=invite)
    if alert(content=invited_alert, 
             title="", 
             buttons=[], large=True, dismissible=False):
      if not user:
        method = invited_signup(invite)
      if anvil.users.get_user():
        open_form('LoginForm')
  else:
    alert(" ".join(errors)) #This is not a valid invite link."