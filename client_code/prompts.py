from anvil import *


def get(spec_dict):
  if spec_dict["name"] == "phone":
    def add_phone():
      top_form = get_open_form()
      top_form.go_settings()
      top_form.content.phone_text_box.focus()
    return {"markdown": "Confirm a phone number to unlock basic empathy.chat features", 
            "tooltip": "We require a phone number to verify identity and foster trust",
            "dismissable": True,
            "background": "theme:Light Blue",
            "click_fn": add_phone,
           }
  else:
    print("Warning: No prompt matches that spec_dict")
    return None

