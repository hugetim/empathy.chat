from ._anvil_designer import MyGroupMembersTemplate
from anvil import *
from .... import network_controller as nc
from .... import glob
from ....groups import MyGroupMember

class MyGroupMembers(MyGroupMembersTemplate):
  def __init__(self, menu, **properties):
    # Set Form properties and Data Bindings.
    self.group = menu.selected_group
    self.my_groups_menu = menu
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.update()
    self.repeating_panel_1.set_event_handler('x-reset', self.reset)
    self.repeating_panel_1.set_event_handler('x-remove_member', self.remove_member)

  def update(self):
    port_members = [nc.my_group_member(**member_dict) for member_dict in self.group.members]
    sorted_port_members = sorted(port_members, key=lambda pu: pu['last_active'], reverse=True)
    self.repeating_panel_1.items = sorted_port_members

  def reset(self, **event_args):
    glob.update_lazy_vars()
    self.update()

  def remove_member(self, member: MyGroupMember, **event_args):
    self.group.members.remove(dict(member_id=member.user_id,
                                   group_id=member.group_id,
                                   guest_allowed=member.guest_allowed,
                                  ))
    self.reset()
    