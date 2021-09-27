from anvil import *


def get(spec_dict):
  if spec_dict["name"] = "phone":
    def add_phone():
      top_form = get_open_form()
      top_form.go_settings()
      top_form.content.phone_text_box.focus()
    return {"markdown": "Confirming a phone number", 
            "dismissable": True,
            "background": "theme:Light Blue",
            "click_fn": add_phone,
           }
