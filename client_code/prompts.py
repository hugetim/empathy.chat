from anvil import *
import anvil.server
from .MenuForm.NetworkMenu.Invite import Invite
from .Dialogs.Invited import Invited
from functools import partial


def invite_dialog(name="", user_id=""):
  """Specifying a `name` leads to connect-existing-user dialog"""
  item = {"relationship": "", "phone_last4": "", "name": name, "user_id": user_id}
  top_form = get_open_form()
  top_form.invite_alert = Invite(item=item)
  return alert(content=top_form.invite_alert,
               title="Invite a close connection to empathy.chat",
               buttons=[], large=True, dismissible=False)

  
def invited_dialog(inviter, inviter_id, rel):
  item = {"relationship": "", "phone_last4": "", "name": inviter, "inviter_id": inviter_id,
          "relationship1to2": rel, "inviter": inviter, "link_key": ""}
  top_form = get_open_form()
  top_form.invited_alert = Invited(item=item)
  return alert(content=top_form.invited_alert,
               title="Accept this invitation to connect?",
               buttons=[], large=True, dismissible=False)
  
  
def get(spec_dict):
  def add_phone():
    top_form = get_open_form()
    top_form.go_settings()
    top_form.content.phone_form.phone_text_box.focus()
  if spec_dict["name"] == "phone":
    return {"markdown": "Confirm a phone number to unlock basic empathy.chat features", 
            "tooltip": "We require a phone number to verify identity and foster trust",
            "dismissable": False, ################### TEMPORARY
            "background": "theme:Light Blue",
            "click_fn": add_phone,
           }
  elif spec_dict["name"] == "phone-invited":
    return {"markdown": ("Confirm a phone number to complete your connection "
                         f"to {spec_dict['inviter']} and unlock basic empathy.chat features"), 
            "tooltip": "We require a phone number to verify identity and foster trust",
            "dismissable": False, ################### TEMPORARY
            "background": "theme:Light Blue",
            "click_fn": add_phone,
           }
  elif spec_dict["name"] == "invited":
    return {"markdown": (f"{spec_dict['inviter']} has requested to add you as a close connection. "
                         "Click to confirm and complete this connection."), 
            "tooltip": f"Connect to {spec_dict['inviter']} and their network",
            "dismissable": False, ################### TEMPORARY
            "background": "theme:Light Mint",
            "click_fn": partial(invited_dialog, spec_dict["inviter"], spec_dict["inviter_id"], spec_dict["rel"]),
           }
  elif spec_dict["name"] == "invite-close":
    return {"markdown": "Invite a new close connection to join you on empathy.chat", 
            "tooltip": "Do you have an empathy buddy you haven't invited yet?",
            "dismissable": False, ################### TEMPORARY
            "background": "theme:Light Mint",
            "click_fn": invite_dialog,
           }
  elif spec_dict["name"] == "member-chat":
    def propose_members():
      top_form = get_open_form()
      top_form.content.propose(specified_users=[portu.user_id for portu in spec_dict["members"]])
    return {"markdown": ("To become a full empathy.chat Member, which allows you to chat "
                         "with a broader network beyond your direct connections, "
                         "please complete an empathy chat with a current Member like: "
                         f"{', '.join([portu.name for portu in spec_dict['members']])}"), 
            "tooltip": "We require this to verify identity and foster trust. Click to propose an empathy exchange.",
            "dismissable": False, ################### TEMPORARY
            "background": "theme:Light Blue",
            "click_fn": propose_members,
           }
  elif spec_dict["name"] == "connected":
    def go_to_their_profile():
      get_open_form().go_profile(spec_dict['to_id'])
    return {"markdown": (f"You are now connected to {spec_dict['to_name']}, "
                         f"who described you as their {spec_dict['rel']}."
                        ), 
            "tooltip": "",
            "dismissable": spec_dict['prompt_id'], ################### TEMPORARY
            "background": "theme:Light Mint",
            "click_fn": go_to_their_profile,
           }
  elif spec_dict["name"] == "message":
    def go_to_message():
      get_open_form().go_profile(spec_dict['from_id'])
      get_open_form().content.go_history()
    return {"markdown": f"You have a new message from {spec_dict['from_name']}.", 
            "tooltip": "Click to see the new message",
            "dismissable": spec_dict['prompt_id'], ################### TEMPORARY
            "background": "",
            "click_fn": go_to_message,
           }
  else:
    print("Warning: No prompt matches that spec_dict")
    return None

