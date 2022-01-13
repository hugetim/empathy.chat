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
  print(f"serve_my_groups: {method}({kwargs}) called on {port_my_groups}")
  my_groups = MyGroups(port_my_groups)
  my_groups.relay(method, kwargs)
  return my_groups.portable()


@sm.authenticated_callable
@anvil.tables.in_transaction
def serve_my_group(port_my_group, method, kwargs):
  print(f"serve_my_group: {method}({kwargs}) called on {port_my_group}")
  my_group = MyGroup(port_my_group)
  my_group.relay(method, kwargs)
  return my_group.portable()


@sm.authenticated_callable
@anvil.tables.in_transaction
def serve_group_invite(port_invite, method, kwargs):
  print(f"serve_group_invite: {method}({kwargs}) called on {port_invite}")
  invite = Invite(port_invite)
  invite.relay(method, kwargs)
  return invite.portable()


class MyGroups(sm.ServerItem, groups.MyGroups): 
  def __init__(self, port_my_groups):
    self.groups = [MyGroup(port_group) for port_group in port_my_groups.groups]

  def portable(self):
    port = groups.MyGroups()
    port.groups = [group.portable() for group in self.groups]
    return port  
    
  def load(self, user_id=""):
    user = sm.get_user(user_id)
    rows = app_tables.groups.search(hosts=user)
    self.groups = []
    for row in rows:
      self.groups.append(groups_server.Group.from_group_row(row, portable=True))

      
class MyGroup(sm.ServerItem, groups.MyGroup): 
  def __init__(self, port_my_group):
    self.update(port_my_group)
    self.members = [port_member.s_user for port_member in port_my_group.members]
    self.invites = [Invite(port_invite) for port_invite in port_my_group.invites]

  def portable(self):
    port = groups.MyGroup()
    port.update(self)
    port.members = [sm.get_port_user(member) for member in self.members]
    port.invites = [invite.portable() for invite in self.invites]
    return port 
  
  @staticmethod
  def from_group_row(group_row, portable=False, user_id=""):
    port_members = [sm.get_port_user(m['user'], user1_id=user_id)
                    for m in app_tables.group_members.search(group=group_row)]
    port_invites = [Invite.from_invite_row(i_row)
                    for i_row in app_tables.group_invites.search(group=group_row)]
    port_group = groups.MyGroup(name=group_row['name'],
                                group_id=group_row.get_id(),
                                members=port_members,
                                invites=port_invites,
                               )
    return port_group if portable else MyGroup(port_group)
  
  
class Invite(sm.ServerItem, groups.Invite): 
  def __init__(self, port_invite):
    self.update(port_invite)

  def portable(self):
    port = groups.Invite()
    port.update(self)
    return port 
  
  @staticmethod
  def from_invite_row(invite_row, portable=False):
    port_invite = groups.Invite(link_key=invite_row['link_key'],
                                invite_id=invite_row.get_id(),
                                expire_date=invite_row['expire_date'],
                                spec=invite_row['spec'],
                               )
    return port_invite if portable else Invite(port_invite)