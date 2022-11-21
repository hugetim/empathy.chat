import anvil.users
import anvil.tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from . import groups
from . import server_misc as sm
from . import accounts
from . import parameters as p
from . import helper as h
from . import portable as port
from .relationship import Relationship
from .exceptions import RowMissingError, ExpiredInviteError, MistakenVisitError


def check_my_group_auth():
  user = sm.get_acting_user()
  if not user or user['trust_level'] < 4:
    raise anvil.users.AuthenticationFailed("User not authorized to manage own groups.")

    
@anvil.server.callable
def serve_group_invite(port_invite, method, kwargs):
  print(f"serve_group_invite: {method}({kwargs}) called on {port_invite}")
  invite = Invite(port_invite)
  invite.relay(method, kwargs)
  return invite.portable()


class MyGroups(groups.MyGroups): 
  def __init__(self, port_my_groups):
    self._groups = [MyGroup(port_group) for port_group in port_my_groups]
    self.names_taken = port_my_groups.names_taken

  def portable(self):
    port = groups.MyGroups()
    port._groups = [group.portable() for group in self]
    port.names_taken = self.names_taken
    return port  

    
def get_names_taken():
  return [row['name'] for row in app_tables.groups.search(current=True)]


@sm.authenticated_callable
@anvil.tables.in_transaction(relaxed=True)
def load_my_groups(user_id="", user=None):
  print(f"load_my_groups({user_id})")
  if not user:
    user = sm.get_acting_user(user_id)
  rows = app_tables.groups.search(hosts=[user], current=True)
  _groups = [MyGroup.from_group_row(row, portable=True, user=user) for row in rows]
  return groups.MyGroups(_groups, get_names_taken())


@sm.authenticated_callable
@anvil.tables.in_transaction
def add_my_group(port_my_groups, user_id=""):
  print(f"add_my_group(port_my_groups, {user_id})")
  check_my_group_auth()
  user = sm.get_acting_user(user_id)
  my_groups = MyGroups(port_my_groups)
  new_row = app_tables.groups.add_row(hosts=[user],
                                      created=sm.now(),
                                      name="",
                                      current=True,
                                     )
  my_groups._groups.append(MyGroup.from_group_row(new_row))
  my_groups.names_taken = get_names_taken()
  return my_groups.portable()
    
      
class MyGroup(groups.MyGroup): 
  def __init__(self, port_my_group):
    self.update(port_my_group)
    self.members = [app_tables.users.get_by_id(member_dict['member_id']) for member_dict in port_my_group.members]
    self.invites = [Invite(port_invite) for port_invite in port_my_group.invites]

  def portable(self):
    port = groups.MyGroup()
    port.update(self)
    port.members = list(member_dicts_from_group_row(self.group_row))
    port.invites = [invite.portable() for invite in self.invites]
    return port

  @property
  def group_row(self):
    return app_tables.groups.get_by_id(self.group_id) if self.group_id else None
  
  @staticmethod
  def from_group_row(group_row, portable=False, user=None):
    if not user:
      user = sm.get_acting_user()
    port_members = list(member_dicts_from_group_row(group_row))
    port_invites = [Invite.from_invite_row(i_row, portable=True, user=user)
                    for i_row in app_tables.group_invites.search(anvil.tables.order_by('expire_date', ascending=False), 
                                                                 group=group_row, current=True)]
    port_my_group = groups.MyGroup(name=group_row['name'],
                                   group_id=group_row.get_id(),
                                   members=port_members,
                                   invites=port_invites,
                                  )
    return port_my_group if portable else MyGroup(port_my_group)

  @staticmethod
  def add_member(user, invite_row):
    if user not in all_members_from_group_row(invite_row['group']):
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


@sm.authenticated_callable
@anvil.tables.in_transaction
def save_my_group_settings(group_id, name, user_id=""):
  print(f"save_my_group_settings({group_id}, {name}, {user_id})")
  check_my_group_auth()
  user = sm.get_acting_user(user_id)
  app_tables.groups.get_by_id(group_id)['name'] = name


@sm.authenticated_callable
@anvil.tables.in_transaction
def create_group_invite(port_my_group):
  print(f"create_group_invite({port_my_group!r})")
  check_my_group_auth()
  my_group = MyGroup(port_my_group)
  from datetime import timedelta
  now = sm.now()
  new_row = app_tables.group_invites.add_row(created=now,
                                             expire_date=now+timedelta(days=30),
                                             group=my_group.group_row,
                                             link_key=new_link_key(),
                                             current=True,
                                            )
  my_group.invites.insert(0, Invite.from_invite_row(new_row))
  return my_group.portable()


def new_link_key():
  unique_key_found = False
  while not unique_key_found:
    random_key = sm.random_code(num_chars=p.NEW_LINK_KEY_LENGTH)
    matching_rows = app_tables.group_invites.search(link_key=random_key)
    unique_key_found = not len(matching_rows)
  return random_key


@sm.authenticated_callable
def delete_group(port_my_group):
  user = sm.get_acting_user()
  my_group = MyGroup(port_my_group)
  if user in my_group.group_row['hosts']:
    my_group.group_row.delete()

      
def all_members_from_group_row(group_row):
  """Returns all group members regardless of trust_level or allowed status"""
  member_set = {m['user'] for m in app_tables.group_members.search(group=group_row)}
  member_set.update(set(group_row['hosts']))
  return list(member_set)


def member_dicts_from_group_row(group_row):
  """Returns dicts for members (excluding hosts) with non-missing trust_level"""
  member_rows = [m for m in app_tables.group_members.search(group=group_row) if m['user']['trust_level']]
  member_ids = [m['user'].get_id() for m in member_rows]
  group_id = group_row.get_id()
  for i, member_id in enumerate(member_ids):
    yield dict(member_id=member_id, group_id=group_id, guest_allowed=member_rows[i]['guest_allowed'])
  

def user_groups(user):
  """Returns all groups for which user in all_members_from_group_row"""
  memberships = {m['group'] for m in app_tables.group_members.search(user=user)}
  hosteds = {group for group in app_tables.groups.search(hosts=[user], current=True)}
  return memberships.union(hosteds)


def allowed_members_from_group_row(group_row, user):
  """Returns group members allowed to interact with `user`"""
  group_hosts = group_row['hosts']
  if user in group_hosts:
    member_set = (
      {m['user'] for m in app_tables.group_members.search(group=group_row) 
       if m['user']['trust_level'] and m['user']['trust_level'] >= 1}
    )
    member_set.update(set(group_row['hosts']))
  elif user_allowed_in_group(user, group_row):
    member_set = (
      {m['user'] for m in app_tables.group_members.search(group=group_row) 
       if m['user']['trust_level'] and (m['user']['trust_level'] >= 2 or (m['user']['trust_level'] >= 1 and m['guest_allowed']))}
    )
    member_set.update(set(group_row['hosts']))
  else:
    member_set = {user}
    if user['trust_level'] and user['trust_level'] >= 1:
      member_set.update(set(group_hosts))
  return list(member_set)


def _guest_allowed_in_group(user, group_row):
  member_record = app_tables.group_members.get(user=user, group=group_row)
  if not member_record:
    sm.warning(f"_guest_allowed_in_group({user['email']}, {group_row['name']}): member_record not found")
  return member_record['guest_allowed']


def user_allowed_in_group(user, group_row):
  return (user['trust_level'] 
          and (user['trust_level'] >= 2 
               or (user['trust_level'] >= 1 and _guest_allowed_in_group(user, group_row))
              )
         )

  
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


@anvil.server.callable
def visit_group_invite_link(link_key, user):
  invite = _get_invite_from_link_key(link_key)
  group_name, group_host_name = invite.visit(user)
  return invite.portable(), group_name, group_host_name


def _get_invite_from_link_key(link_key):
  port_invite = groups.Invite(link_key=link_key)
  return Invite(port_invite)


class Invite(sm.ServerItem, groups.Invite): 
  def __init__(self, port_invite):
    self.update(port_invite)

  def portable(self):
    port = groups.Invite()
    port.update(self)
    return port 

  def _invite_row(self):
    row = None
    if self.invite_id:
      row = app_tables.group_invites.get_by_id(self.invite_id)
      if not row:
        raise RowMissingError("Invalid group invite id.")
    elif self.link_key:
      row = app_tables.group_invites.get(link_key=self.link_key, current=True)
      if not row:
        raise RowMissingError("Invalid group invite link.")
    else:
      raise RowMissingError("Not enough information to retrieve group_invite row.")
    return row

  def _unexpired_invite_row(self):
    invite_row = self._invite_row()
    if invite_row['expire_date'] < sm.now():
      raise ExpiredInviteError("This group invite link is expired.")
    return invite_row
  
  def expire_date_update(self):
    row = self._invite_row()
    row['expire_date'] = self.expire_date

  def authorizes_signup(self):
    try:
      invite_row = self._invite_row()
    except RowMissingError:
      return False
    if invite_row['link_key'] != self.link_key or invite_row.get_id() != self.invite_id:
      return False
    if invite_row['expire_date'] < sm.now():
      return False
    return True
  
  def register(self, user):
    invite_row = self._unexpired_invite_row()
    sm.my_assert(user, "register assumes a user")
    Invite._register_user(user)
    Invite._add_visitor(user, invite_row)
  
  def visit(self, user):
    invite_row = self._unexpired_invite_row()
    self.invite_id = invite_row.get_id()
    if user:
      Invite._add_visitor(user, invite_row)
    return self._group_name_and_host(invite_row)

  @staticmethod
  @anvil.tables.in_transaction
  def _add_visitor(user, invite_row):
    if user in invite_row['group']['hosts']:
      this_group = invite_row['group']
      raise MistakenVisitError(f"You have clicked/visited an invite link for a group you are a host of: {this_group['name']}.\n\n"
                                f"To invite someone else to join your group, instead send this group invite link to them "
                                "so they can visit the url, which will enable them to join the group (and also to create "
                                "an empathy.chat account if they are new)."
                              )
    MyGroup.add_member(user, invite_row)


  def _group_name_and_host(self, invite_row):
    this_group = invite_row['group']
    rel = Relationship(group_host_to_member=True)
    return this_group['name'], sm.name(this_group['hosts'][0], rel=rel)

  
  @staticmethod
  @anvil.tables.in_transaction
  def _register_user(user):
    accounts.init_user_info(user)
      
  @staticmethod
  def from_invite_row(invite_row, portable=False, user=None):
    if not user:
      user = sm.get_acting_user(user_id)
    port_invite = groups.Invite(link_key=invite_row['link_key'],
                                invite_id=invite_row.get_id(),
                                expire_date=sm.as_user_tz(invite_row['expire_date'], user),
                                spec=invite_row['spec'],
                                create_date=sm.as_user_tz(invite_row['created'], user),
                               )
    return port_invite if portable else Invite(port_invite)
