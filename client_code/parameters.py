import anvil.users
import anvil.server
from anvil import app


BUFFER_SECONDS = 7
DEBUG_MODE = (app.environment.name[0:5] == "Debug")
CONFIRM_MATCH_SECONDS = 15 if DEBUG_MODE else 60
WAIT_SECONDS = 55 if DEBUG_MODE else 60*20
ASSUME_INACTIVE_DAYS = 60 # 30 day persistent login + 30 days
MIN_BETWEEN_R_EM = 20
CONTACT_EMAIL = "support@empathy.chat"
URL = "https://e6hfysk4hhri7btc.anvil.app/VRLRQKFZAS4J7LXXZPU2FWPI" if DEBUG_MODE else "https://empathy.chat"
URL_WITH_ALT = URL
SELECTED_TAB_COLOR = "theme:White"
NONSELECTED_TAB_COLOR = "theme:Gray 200"
START_EARLY_MINUTES = 5
MIN_RELATIONSHIP_LENGTH = 3
