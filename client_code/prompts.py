from anvil import *
from .MenuForm.NetworkMenu.Invite import Invite


def get(spec_dict):
  if spec_dict["name"] == "phone":
    def add_phone():
      top_form = get_open_form()
      top_form.go_settings()
      top_form.content.phone_form.phone_text_box.focus()
    return {"markdown": "Confirm a phone number to unlock basic empathy.chat features", 
            "tooltip": "We require a phone number to verify identity and foster trust",
            "dismissable": False, ################### TEMPORARY
            "background": "theme:Light Blue",
            "click_fn": add_phone,
           }
  elif spec_dict["name"] == "invite_close":
    def invite_dialog():
      item = {"relationship": "", "phone_last4": ""}
      alert(content=Invite(item=item), title="Invite a close connection to empathy.chat", buttons=[], large=True, dismissible=False)
    return {"markdown": "Invite a new close connection to join you on empathy.chat", 
            "tooltip": "Do you have an empathy buddy you haven't invited yet?",
            "dismissable": False, ################### TEMPORARY
            "background": "theme:Light Mint",
            "click_fn": invite_dialog,
           }
  else:
    print("Warning: No prompt matches that spec_dict")
    return None

