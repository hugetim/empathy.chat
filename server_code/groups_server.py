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
from .exceptions import RowMissingError, ExpiredInviteError, MistakenVisitError, InvalidInviteError
from functools import lru_cache


def check_my_group_auth(group_id=None):
  user = sm.get_acting_user()
  if not user or user['trust_level'] < 4:
    raise anvil.users.AuthenticationFailed("User not authorized to manage own groups.")
  if group_id and user not in app_tables.groups.get_by_id(group_id)['hosts']:
    raise anvil.users.AuthenticationFailed("User not authorized to manage this group.")

    
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
  return [row['name'] for row in app_tables.groups.search(q.fetch_only('name'), current=True)]


@sm.authenticated_callable
@anvil.tables.in_transaction(relaxed=True)
def load_my_groups(user_id="", user=None):
  print(f"load_my_groups({user_id})")
  if not user:
    user = sm.get_acting_user(user_id)
  rows = app_tables.groups.search(q.fetch_only('name', hosts=q.fetch_only('first_name')), hosts=[user], current=True)
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
    self.members = [sm.get_other_user(member_dict['member_id']) for member_dict in port_my_group.members]
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
    port_invites = [Invite.from_invite_row(i_row, portable=True, user=user)
                    for i_row in app_tables.group_invites.search(q.fetch_only('link_key', 'spec', 'created', 'expire_date'), anvil.tables.order_by('expire_date', ascending=False), 
                                                                 group=group_row, current=True)]
    port_my_group = groups.MyGroup(name=group_row['name'],
                                   group_id=group_row.get_id(),
                                   members=list(member_dicts_from_group_row(group_row)),
                                   invites=port_invites,
                                  )
    return port_my_group if portable else MyGroup(port_my_group)

  @staticmethod
  def add_member(user, invite_row):
    if user not in all_members_from_group_row(invite_row['group']):
      guest_allowed = invite_row['spec'].get('guest_allowed')
      app_tables.group_members.add_row(user=user,
                                       group=invite_row['group'],
                                       invite=invite_row,
                                       guest_allowed=guest_allowed,
                                      )
    else:
      this_group = invite_row['group']
      host_name = sm.name(this_group['hosts'][0], user)
      raise MistakenVisitError(f"You are already a member of {host_name}'s {this_group['name']} group. "
                               f"You no longer need use this group invite link. Simply visit {p.URL} instead."
                              )


@sm.authenticated_callable
@anvil.tables.in_transaction(relaxed=True)
def save_my_group_settings(group_id, name, user_id=""):
  print(f"save_my_group_settings({group_id}, {name}, {user_id})")
  check_my_group_auth(group_id)
  user = sm.get_acting_user(user_id)
  app_tables.groups.get_by_id(group_id)['name'] = name.strip()


@sm.authenticated_callable
@anvil.tables.in_transaction(relaxed=True)
def create_group_invite(port_my_group):
  print(f"create_group_invite({port_my_group!r})")
  check_my_group_auth(port_my_group.group_id)
  my_group = MyGroup(port_my_group)
  from datetime import timedelta
  now = sm.now()
  new_row = app_tables.group_invites.add_row(created=now,
                                             expire_date=now+timedelta(days=30),
                                             group=my_group.group_row,
                                             link_key=new_link_key(),
                                             spec={},
                                             current=True,
                                            )
  my_group.invites.insert(0, Invite.from_invite_row(new_row))
  return my_group.portable()


def new_link_key():
  unique_key_found = False
  while not unique_key_found:
    random_key = h.random_code(num_chars=p.NEW_LINK_KEY_LENGTH)
    matching_rows = app_tables.group_invites.search(q.fetch_only('link_key'), link_key=random_key)
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
  member_set = {m['user'] for m in app_tables.group_members.search(q.fetch_only(user=q.fetch_only('first_name')), group=group_row)}
  member_set.update(set(group_row['hosts']))
  return list(member_set)


def member_dicts_from_group_row(group_row):
  """Returns dicts for members (excluding hosts) with non-missing trust_level"""
  member_rows = [m for m in app_tables.group_members.search(q.fetch_only('guest_allowed', user=q.fetch_only('first_name', 'trust_level')), group=group_row) if m['user']['trust_level']]
  member_ids = [m['user'].get_id() for m in member_rows]
  group_id = group_row.get_id()
  for i, member_id in enumerate(member_ids):
    yield dict(member_id=member_id, group_id=group_id, guest_allowed=member_rows[i]['guest_allowed'])
  

def _user_groups(user):
  """Returns all groups for which user in all_members_from_group_row"""
  group_fetch = q.fetch_only('name', 'hosts')
  memberships = {m['group'] for m in app_tables.group_members.search(q.fetch_only(group=group_fetch), user=user)}
  hosteds = {group for group in app_tables.groups.search(group_fetch, hosts=[user], current=True)}
  return memberships.union(hosteds)


@lru_cache(maxsize=None)
def allowed_members_from_group_row(group_row, user):
  """Returns group members allowed to interact with `user`"""
  group_hosts_set = set(group_row['hosts'])
  if user in group_hosts_set:
    member_set = (
      {m['user'] for m in app_tables.group_members.search(q.fetch_only('user'), group=group_row) 
       if m['user']['trust_level'] and m['user']['trust_level'] >= 1}
    )
    member_set.update(group_hosts_set)
  elif user_allowed_in_group(user, group_row):
    member_set = (
      {m['user'] for m in app_tables.group_members.search(q.fetch_only('guest_allowed', 'user'), group=group_row) 
       if m['user']['trust_level'] and (m['user']['trust_level'] >= 2 or (m['user']['trust_level'] >= 1 and m['guest_allowed']))}
    )
    member_set.update(group_hosts_set)
  else:
    member_set = {user}
    if user['trust_level'] and user['trust_level'] >= 1:
      member_set.update(group_hosts_set)
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


def group_relationships(other_users, user):
  allowed_members_to_groups = _group_info(other_users, user)
  gr_dict = {}
  for user2 in other_users:
    gr_dict[user2] = _group_relationship(user2, user, allowed_members_to_groups[user2])
  return gr_dict


def _group_relationship(user2, user, common_groups):
  return _group_tie_level_to_relationship(_group_tie_level(user2, user, common_groups))


def _group_tie_level(user2, user, groups_allowed_in):
  for group_row in groups_allowed_in:
    if {user2, user} & set(group_row['hosts']):
      return 3
    else:
      return 2
  return 0


def _group_tie_level_to_relationship(group_tie_level):  
  return dict(
    group_host_to_member=(group_tie_level >= 3),
    group_authorized=(group_tie_level >= 1),
    group_authorized_pair=(group_tie_level >= 2),
  )


def _group_info(other_users, user):
  import collections
  allowed_members_to_groups = collections.defaultdict(list)
  for group_row, group_members in groups_and_allowed_members(user):
    for user2 in set(group_members) & set(other_users):
      allowed_members_to_groups[user2].append(group_row)
  return allowed_members_to_groups


def groups_and_allowed_members(user):
  for group_row in _user_groups(user):
    group_members = {u for u in allowed_members_from_group_row(group_row, user)}
    yield (group_row, group_members)
  
# @sm.authenticated_callable
# def update_guest_allowed(port_member):
#   user = sm.get_acting_user()
#   group_row = app_tables.groups.get_by_id(port_member.group_id)
#   if user not in group_row['hosts']:
#     sm.warning(f"update_guest_allowed not authorized")
#     return
#   user2 = sm.get_other_user(port_member.user_id)
#   member_row = app_tables.group_members.get(user=user2, group=group_row)
#   member_row['guest_allowed'] = port_member.guest_allowed


@sm.authenticated_callable
def leave_group(group_id, user_id):
  user = sm.get_acting_user(user_id)
  _remove_group_member(group_id, user)


def _remove_group_member(group_id, user):
  group_row = app_tables.groups.get_by_id(group_id)
  member_row = app_tables.group_members.get(group=group_row, user=user)
  member_row.delete()


@sm.authenticated_callable
def remove_group_member(my_group_member: groups.MyGroupMember, user_id):
  group_id = my_group_member.group_id
  check_my_group_auth(group_id)
  user2 = sm.get_other_user(my_group_member.user_id)
  _remove_group_member(group_id, user2)
  

@anvil.server.callable
def visit_group_invite_link(link_key, user):
  invite = _get_invite_from_link_key(link_key)
  group_name, group_host_name = invite.visit(user)
  return invite.portable(), group_name, group_host_name


def _get_invite_from_link_key(link_key):
  port_invite = groups.Invite(link_key=link_key)
  return Invite(port_invite)


class Invite(sm.ServerItem, groups.Invite):
  not_authorized_message = "Sorry, signup is not authorized by this invite."
  
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

  def authorizes_signup(self, email=""):
    try:
      invite_row = self._invite_row()
    except RowMissingError:
      return False
    if invite_row['link_key'] != self.link_key or invite_row.get_id() != self.invite_id:
      return False
    if invite_row['expire_date'] < sm.now():
      return False
    emails_allowed = invite_row['spec'].get('emails_allowed')
    if emails_allowed is not None and not accounts.in_email_list(email, emails_allowed):
      self.not_authorized_message = f"Sorry, signup for {email} is not authorized by this invite."
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
    emails_allowed = invite_row['spec'].get('emails_allowed')
    email = user['email']
    if emails_allowed is not None and not accounts.in_email_list(email, emails_allowed):
      raise InvalidInviteError(f"Sorry, {email} is not authorized by this invite.")
    MyGroup.add_member(user, invite_row)


  def _group_name_and_host(self, invite_row):
    this_group = invite_row['group']
    rel = Relationship(group_host_to_member=True)
    return this_group['name'], sm.name(this_group['hosts'][0], rel=rel)

  
  @staticmethod
  @anvil.tables.in_transaction(relaxed=True)
  def _register_user(user):
    accounts.init_user_info(user)
      
  @staticmethod
  def from_invite_row(invite_row, portable=False, user=None):
    if not user:
      user = sm.get_acting_user()
    port_invite = groups.Invite(link_key=invite_row['link_key'],
                                invite_id=invite_row.get_id(),
                                expire_date=sm.as_user_tz(invite_row['expire_date'], user),
                                spec=invite_row['spec'],
                                create_date=sm.as_user_tz(invite_row['created'], user),
                               )
    return port_invite if portable else Invite(port_invite)
