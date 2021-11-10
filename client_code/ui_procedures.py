from anvil import *
import anvil.server


def disconnect_flow(user2_id, user2_name, user1_id=""):
  if confirm(f"Really remove your connection to {user2_name}? This cannot be undone."):
    return anvil.server.call('disconnect', user2_id, user1_id)
  else:
    return False

      
def reload():
  """Resest app after any potential change to trust_level or prompts"""
  init_dict = anvil.server.call('init')
  open_form('MenuForm', item=init_dict)
  