from anvil import *
import anvil.server
from .groups import MyGroupMember


def remove_member_flow(my_group_member: MyGroupMember, user1_id=""):
  if confirm(f"Really remove {my_group_member.name}? This cannot be undone."):
    anvil.server.call('remove_group_member', my_group_member, user1_id)
    return True
  else:
    return False
