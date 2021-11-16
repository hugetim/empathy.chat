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
URL_WITH_ALT = "https://empathy.chat"
URL = "https://empathy.chat"
SELECTED_TAB_COLOR = "theme:White"
NONSELECTED_TAB_COLOR = "theme:Gray 200"
START_EARLY_MINUTES = 5
DATE_FORMAT = "%m/%d/%Y"
