import anvil.users
import anvil.server
from anvil import app


BUFFER_SECONDS = 7
DEBUG_MODE = (app.environment.name[0:5] == "Debug")
CONFIRM_MATCH_SECONDS = 15 if DEBUG_MODE else 60
WAIT_SECONDS = 55 #if DEBUG_MODE else 60*20
ASSUME_INACTIVE_DAYS = 60 # 30 day persistent login + 30 days
ASSUME_COMPLETE_HOURS = 4
MIN_BETWEEN_R_EM = 20
CONTACT_EMAIL = "support@empathy.chat"
URL = "https://e6hfysk4hhri7btc.anvil.app/VRLRQKFZAS4J7LXXZPU2FWPI" if DEBUG_MODE else "https://empathy.chat"
SELECTED_TAB_COLOR = "theme:White"
NONSELECTED_TAB_COLOR = "theme:Gray 200"
START_EARLY_MINUTES = 5
MIN_RELATIONSHIP_LENGTH = 3
MISTAKEN_INVITER_GUESS_ERROR = (
  "The inviter did not accurately provide the last 4 digits of your phone number."
)
TRUST_TOOLTIP = {"Visitor": "Has not yet confirmed an email address",
                 "Guest": "Has not yet confirmed a phone number",
                 "Confirmed": "Has not yet had an empathy chat with a Member (who can verify their identity)",
                 "Member": ("Has confirmed an email address and phone number" 
                            "and matched with a Member who can verify their identity"),
                 "Partner": "Confirmed url and has contributed in some way",
                 "Admin": "empathy.chat admin"
                }