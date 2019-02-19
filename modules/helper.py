import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import datetime
import parameters as p
import anvil.tz


def seconds_left(status, last_confirmed, ping_start=None):
    now = datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc())
    if status in ["pinging", "pinged"]:
      confirm_match = p.CONFIRM_MATCH_SECONDS - (now - ping_start).seconds
      if status == "pinging":
        return confirm_match + 2*p.BUFFER_SECONDS
      elif status == "pinged":
        return confirm_match + p.BUFFER_SECONDS
    if status == "requesting":
      return p.WAIT_SECONDS - (now - last_confirmed).seconds
    else:
      print("helper.seconds_left(s,lc,ps): " + status)
