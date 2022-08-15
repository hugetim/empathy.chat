import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from . import groups
from . import server_misc as sm
from . import accounts
from . import parameters as p
from . import helper as h
from . import portable as port
from .exceptions import RowMissingError, ExpiredInviteError, MistakenVisitError


@sm.authenticated_callable
@anvil.tables.in_transaction
def serve_my_groups(port_my_groups, method, kwargs):
  if sm.DEBUG:
    print(f"serve_my_groups: {method}({kwargs}) called on {port_my_groups}")
  else:
    print(f"serve_my_groups: {method}({kwargs})")
  check_my_group_auth()
  my_groups = MyGroups(port_my_groups)
  my_groups.relay(method, kwargs)
  return my_groups.portable()


@sm.authenticated_callable
@anvil.tables.in_transaction
def serve_my_group(port_my_group, method, kwargs):
  print(f"serve_my_group: {method}({kwargs}) called on {port_my_group}")
  check_my_group_auth()
  my_group = MyGroup(port_my_group)
  my_group.relay(method, kwargs)
  return my_group.portable()


def check_my_group_auth():
  user = anvil.users.get_user()
  if not user or user['trust_level'] < 4:
    raise(anvil.users.AuthenticationFailed("User not authorized to manage own groups."))

    
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
    user = sm.get_acting_user(user_id)
    rows = app_tables.groups.search(hosts=[user], current=True)
    self._groups = [MyGroup.from_group_row(row) for row in rows]
    
  def update_names_taken(self):
    self.names_taken = [row['name'] for row in app_tables.groups.search(current=True)]

  def add(self, user_id=""):
    user = sm.get_acting_user(user_id)
    new_row = app_tables.groups.add_row(hosts=[user],
                                        created=sm.now(),
                                        name="",
                                        current=True,
                                       )
    self._groups.append(MyGroup.from_group_row(new_row))
    
      
class MyGroup(sm.ServerItem, groups.MyGroup): 
  def __init__(self, port_my_group):
    self.update(port_my_group)
    self.members = [app_tables.users.get_by_id(member_dict['member_id']) for member_dict in port_my_group.members]
    self.invites = [Invite(port_invite) for port_invite in port_my_group.invites]

  def portable(self):
    port = groups.MyGroup()
    port.update(self)
    #port.members = sm.get_port_users_full(self.members)
    port.members = list(member_dicts_from_group_row(self.group_row))
    port.invites = [invite.portable() for invite in self.invites]
    return port

  @property
  def group_row(self):
    return app_tables.groups.get_by_id(self.group_id) if self.group_id else None
  
  def save_settings(self, user_id=""):
    user = sm.get_acting_user(user_id)
    self.group_row['name'] = self.name
    
  def delete(self, user_id=""):
    user = sm.get_acting_user(user_id)
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
    self.invites.insert(0, Invite.from_invite_row(new_row))

  @staticmethod
  def from_group_row(group_row, portable=False, user_id=""):
    port_members = list(member_dicts_from_group_row(group_row))
    port_invites = [Invite.from_invite_row(i_row)
                    for i_row in app_tables.group_invites.search(tables.order_by('expire_date', ascending=False), 
                                                                 group=group_row, current=True)]
    port_my_group = groups.MyGroup(name=group_row['name'],
                                   group_id=group_row.get_id(),
                                   members=port_members,
                                   invites=port_invites,
                                  )
    return port_my_group if portable else MyGroup(port_my_group)

  @staticmethod
  def add_member(user, invite_row):
    if user not in members_from_group_row(invite_row['group'], with_trust_level=False):
      app_tables.group_members.add_row(user=user,
                                       group=invite_row['group'],
                                       invite=invite_row,
                                      )
    else:
      this_group = invite_row['group']
      host_name = sm.name(this_group['hosts'][0], user)
      raise MistakenVisitError(f"You are already a member of {host_name}'s {this_group['name']} group. "
                               f"You no longer need use this group invite link. Simply visit {p.URL} instead."
                              )

      
def members_from_group_row(group_row, with_trust_level=True):
  member_set = (
    {m['user'] for m in app_tables.group_members.search(group=group_row) if m['user']['trust_level']} if with_trust_level
    else {m['user'] for m in app_tables.group_members.search(group=group_row)}
  )
  member_set.update(set(group_row['hosts']))
  return list(member_set)


def member_dicts_from_group_row(group_row):
  member_rows = [m for m in app_tables.group_members.search(group=group_row) if m['user']['trust_level']]
  member_ids = [m['user'] for m in member_rows]
  group_id = group_row.get_id()
  for i, member_id in enumerate(member_ids):
    yield dict(member_id=member_id, group_id=group_id, guest_allowed=member_rows[i]['guest_allowed'])
  

def user_groups(user):
  memberships = {m['group'] for m in app_tables.group_members.search(user=user)}
  hosteds = {group for group in app_tables.groups.search(hosts=[user], current=True)}
  return memberships.union(hosteds)


def get_create_group_items(user):
  items = []
  for g in user_groups(user):
    host = g['hosts'][0]
    subtext = f"(host: {'me' if host == user else sm.name(host, to_user=user)})"
    items.append(dict(key=g['name'], value=groups.Group(g['name'], g.get_id()), subtext=subtext))
  return sorted(items, key=lambda item:(item['subtext'] + item['key']))


def guest_allowed_in_group(user, group_row):
  member_record = app_tables.group_members.get(user=user, group=group_row)
  if not member_record:
    sm.warning(f"guest_allowed_in_group({user['email']}, {group_row['name']}): member_record not found")
  return member_record['guest_allowed']
  
  
@sm.authenticated_callable
def update_guest_allowed(port_member):
  user = sm.get_acting_user()
  group_row = app_tables.groups.get_by_id(port_member.group_id)
  if user not in group_row['hosts']:
    sm.warning(f"update_guest_allowed not authorized")
    return
  user2 = sm.get_other_user(port_member.user_id)
  member_row = app_tables.group_members.get(user=user2, group=group_row)
  member_row['guest_allowed'] = port_member.guest_allowed
  

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

  def expire_date_update(self):
    row = self._invite_row()
    row['expire_date'] = self.expire_date
  
  def visit(self, user, register=False):
    invite_row = self._invite_row()
    if not register and invite_row['expire_date'] < sm.now():
      raise ExpiredInviteError("This group invite link is expired.")
    if invite_row and user:
      if register:
        Invite._register_user(user)
      if user in invite_row['group']['hosts']:
        this_group = invite_row['group']
        raise MistakenVisitError(f"You have clicked/visited an invite link for a group you are a host of: {this_group['name']}.\n\n"
                                 f"To invite someone else to join your group, instead send this group invite link to them "
                                 "so they can visit the url, which will enable them to join the group (and also to create "
                                 "an empathy.chat account if they are new)."
                                )
      Invite._add_visitor(user, invite_row)

  @staticmethod
  @anvil.tables.in_transaction
  def _add_visitor(user, invite_row):
    MyGroup.add_member(user, invite_row)
    
  @staticmethod
  @anvil.tables.in_transaction
  def _register_user(user):
    accounts.init_user_info(user)
      
  @staticmethod
  def from_invite_row(invite_row, portable=False, user_id=""):
    user = sm.get_acting_user(user_id)
    port_invite = groups.Invite(link_key=invite_row['link_key'],
                                invite_id=invite_row.get_id(),
                                expire_date=sm.as_user_tz(invite_row['expire_date'], user),
                                spec=invite_row['spec'],
                                create_date=sm.as_user_tz(invite_row['created'], user),
                               )
    return port_invite if portable else Invite(port_invite)
