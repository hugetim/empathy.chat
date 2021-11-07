from anvil import *
from .MenuForm.NetworkMenu.Invite import Invite


def invite_dialog(name="", user_id=""):
  item = {"relationship": "", "phone_last4": "", "name": name, "user_id": user_id}
  top_form = get_open_form()
  top_form.invite_alert = Invite(item=item)
  alert(content=top_form.invite_alert, 
        title="Invite a close connection to empathy.chat", 
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
  elif spec_dict["name"] == "invite_close":
    return {"markdown": "Invite a new close connection to join you on empathy.chat", 
            "tooltip": "Do you have an empathy buddy you haven't invited yet?",
            "dismissable": False, ################### TEMPORARY
            "background": "theme:Light Mint",
            "click_fn": invite_dialog,
           }
  else:
    print("Warning: No prompt matches that spec_dict")
    return None

