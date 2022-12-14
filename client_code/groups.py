import anvil.server
from anvil import *
from . import helper as h
from . import parameters as p


@anvil.server.portable_class
class Group(h.AttributeToKey):
  def __init__(self, name="", group_id="", members=None, hosts=None):
    self.name = name
    self.group_id = group_id
    self.members = members if members else []
    self.hosts = hosts if hosts else []
    
  def __str__(self):
    return self.name

  def __eq__(self, other):
    return isinstance(other, Group) and self.group_id == other.group_id

  
@anvil.server.portable_class
class MyGroups():
  def __init__(self, groups=None, names_taken=None):
    self._groups = list(groups) if groups else []
    self.names_taken = names_taken if names_taken else []

  def __getitem__(self, position):
    return self._groups[position]
  
  def __len__(self):
    return len(self._groups)

  def __repr__(self):
    return f"MyGroups({self._groups!r}, {self.names_taken!r})"
  
   
@anvil.server.portable_class
class MyGroup(h.AttributeToKey):
  default_name = "New Group"
  
  def __init__(self, name="", group_id="", members=None, invites=None):
    self.name = name
    self.group_id = group_id
    self.members = members if members else []
    self.invites = invites if invites else []
    
  def __str__(self):
    return self.name

  def __repr__(self):
    return f"MyGroup({self.name}, {self.group_id}, {self.members!r}, {self.invites!r})"

  def update(self, new_self):
    for key, value in new_self.__dict__.items():
      setattr(self, key, value)
      

@anvil.server.portable_class
class Invite(h.PortItem, h.AttributeToKey):
  repr_desc = "groups.Invite: "
  server_fn_name = 'serve_group_invite'
  def __init__(self, link_key="", invite_id="", expire_date=None, spec=None, create_date=None):
    self.link_key = link_key
    self.invite_id = invite_id
    self.expire_date = expire_date
    self.spec = spec
    self.create_date = create_date
   
  @property
  def url(self):
    return f"{p.URL}#?group={self.link_key}"
  
  @property
  def create_date_str(self):
    return h.short_date_str(self.create_date)
