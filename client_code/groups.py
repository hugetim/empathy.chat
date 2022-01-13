import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from . import helper as h
from . import parameters as p


@anvil.server.portable_class
class MyGroups(h.AttributeToKey):
  
  def __init__(self, name="New Group", group_id=None, groups=None):
    self.name = name
    self.group_id = group_id
    self.groups = groups if groups else []
    
  def update(self, new_self):
    for key, value in new_self.__dict__.items():
      setattr(self, key, value)

  def __repr__(self):
    return "groups.MyGroups: " + str(self.__dict__)
  
  def relay(self, method, kwargs=None):
    if not kwargs:
      kwargs = {}
    new_object = anvil.server.call('serve_my_groups', self, method, kwargs)
    self.update(new_object)

    
@anvil.server.portable_class
class MyGroup(h.AttributeToKey):
  
  def __init__(self, members=None, invites=None):
    self.members = members if members else []
    self.invites = invites if invites else []
    
  def update(self, new_self):
    for key, value in new_self.__dict__.items():
      setattr(self, key, value)

  def __repr__(self):
    return "groups.MyGroup: " + str(self.__dict__)
  
  def relay(self, method, kwargs=None):
    if not kwargs:
      kwargs = {}
    new_object = anvil.server.call('serve_my_group', self, method, kwargs)
    self.update(new_object)    
    