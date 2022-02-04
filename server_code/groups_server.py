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
from . import helper as h
from .exceptions import RowMissingError, ExpiredInviteError


@sm.authenticated_callable
@anvil.tables.in_transaction
def serve_my_groups(port_my_groups, method, kwargs):
  if sm.DEBUG:
    print(f"serve_my_groups: {method}({kwargs}) called on {port_my_groups}")
  else:
    print(f"serve_my_groups: {method}({kwargs})")
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


@anvil.server.callable
def serve_group_invite(port_invite, method, kwargs):
  print(f"serve_group_invite: {method}({kwargs}) called on {port_invite}")
  invite = Invite(port_invite)
  invite.relay(method, kwargs)
  return invite.portable()


class MyGroups(sm.ServerItem, groups.MyGroups): 
  def __init__(self, port_my_groups):
    self._groups = [MyGroup(port_group) for port_group in port_my_groups]
    self.update_names_taken()

  def portable(self):
    port = groups.MyGroups()
    port._groups = [group.portable() for group in self]
    port.names_taken = self.names_taken
    return port  
    
  def load(self, user_id=""):
    user = sm.get_user(user_id)
    rows = app_tables.groups.search(hosts=[user], current=True)
    self._groups = [MyGroup.from_group_row(row) for row in rows]
    
  def update_names_taken(self):
    self.names_taken = [row['name'] for row in app_tables.groups.search(current=True)]

  def add(self, user_id=""):
    user = sm.get_user(user_id)
    new_row = app_tables.groups.add_row(hosts=[user],
                                        created=sm.now(),
                                        name="",
                                        current=True,
                                       )
    self._groups.append(MyGroup.from_group_row(new_row))
    
      
class MyGroup(sm.ServerItem, groups.MyGroup): 
  def __init__(self, port_my_group):
    self.update(port_my_group)
    self.members = [port_member.s_user for port_member in port_my_group.members]
    self.invites = [Invite(port_invite) for port_invite in port_my_group.invites]

  def portable(self):
    port = groups.MyGroup()
    port.update(self)
    port.members = sm.get_port_users_full(self.members)
    port.invites = [invite.portable() for invite in self.invites]
    return port

  @property
  def group_row(self):
    return app_tables.groups.get_by_id(self.group_id) if self.group_id else None
  
  def save_settings(self, user_id=""):
    user = sm.get_user(user_id)
    self.group_row['name'] = self.name
    
  def delete(self, user_id=""):
    user = sm.get_user(user_id)
    self.group_row.delete()

  def create_invite(self):
    from datetime import timedelta
    now = sm.now()
    new_row = app_tables.group_invites.add_row(created=now,
                                               expire_date=now+timedelta(days=30),
                                               group=self.group_row,
                                               link_key=sm.random_code(num_chars=7),
                                               current=True,
                                              )
    self.invites.append(Invite.from_invite_row(new_row))

  @staticmethod
  def from_group_row(group_row, portable=False, user_id=""):
    port_members = sm.get_port_users_full(MyGroup.members_from_group_row(group_row), user1_id=user_id)
    port_invites = [Invite.from_invite_row(i_row)
                    for i_row in app_tables.group_invites.search(group=group_row, current=True)]
    port_group = groups.MyGroup(name=group_row['name'],
                                group_id=group_row.get_id(),
                                members=port_members,
                                invites=port_invites,
                               )
    return port_group if portable else MyGroup(port_group)
  
  @staticmethod
  def members_from_group_row(group_row):
    member_set = {m['user'] for m in app_tables.group_members.search(group=group_row)}
    member_set.update(set(group_row['hosts']))
    return list(member_set)

  @staticmethod
  def add_member(user, invite_row):
    if user not in MyGroup.members_from_group_row(invite_row['group']):
      app_tables.group_members.add_row(user=user,
                                       group=invite_row['group'],
                                       invite=invite_row,
                                      )  

def user_groups(user):
  memberships = {m['group'] for m in app_tables.group_members.search(user=user)}
  hosteds = {group for group in app_tables.groups.search(hosts=[user], current=True)}
  return memberships.union(hosteds)


def get_create_group_items(user):
  group_rows = sorted(user_groups(user), key=lambda group_row:group_row['name'])
  return [(g['name'], groups.Group(g['name'], g.get_id())) for g in group_rows]
  

class Invite(sm.ServerItem, groups.Invite): 
  def __init__(self, port_invite):
    self.update(port_invite)

  def portable(self):
    port = groups.Invite()
    port.update(self)
    return port 

  def _invite_row(self):
    row = None
    errors = []
    if self.invite_id:
      row = app_tables.group_invites.get_by_id(self.invite_id)
      if not row:
        raise(RowMissingError("Invalid group invite id."))
    elif self.link_key:
      row = app_tables.group_invites.get(link_key=self.link_key, current=True)
      if not row:
        raise(RowMissingError("Invalid group invite link."))
    else:
      raise(RowMissingError("Not enough information to retrieve group_invite row."))
    return row
  
  def visit(self, user, register=False):
    invite_row = self._invite_row()
    if not register and invite_row['expire_date'] < sm.now():
      raise ExpiredInviteError("This group invite link is expired.")
    if invite_row and user:
      if register:
        Invite._register_user(user)
      Invite._add_visitor(user, invite_row)

  @staticmethod
  @anvil.tables.in_transaction
  def _add_visitor(user, invite_row):
    MyGroup.add_member(user, invite_row)
    
  @staticmethod
  @anvil.tables.in_transaction
  def _register_user(user):
    sm.init_user_info(user)
      
  @staticmethod
  def from_invite_row(invite_row, portable=False, user_id=""):
    user = sm.get_user(user_id)
    port_invite = groups.Invite(link_key=invite_row['link_key'],
                                invite_id=invite_row.get_id(),
                                expire_date=sm.as_user_tz(invite_row['expire_date'], user),
                                spec=invite_row['spec'],
                               )
    return port_invite if portable else Invite(port_invite)