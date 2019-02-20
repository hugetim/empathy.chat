#import anvil.google.auth, anvil.google.drive
#from anvil.google.drive import app_files
import datetime
#import parameters as p
#import anvil.tz
import math


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


def seconds_to_digital(seconds):
  minutes = math.floor(seconds / 60)
  seconds -= minutes * 60
  hours = math.floor(minutes / 60)
  minutes -= hours * 60
  output = ""
  minute_str = str(minutes)
  if hours > 0:
    output += str(hours) + ":"
    if minutes < 10:
      minute_str = "0" + minute_str
  output += minute_str + ":"
  second_str = str(seconds)
  if seconds < 10:
    second_str = "0" + second_str
  output += second_str
  return output


def seconds_to_words(seconds):
  minutes = math.floor(seconds / 60)
  seconds -= minutes * 60
  hours = math.floor(minutes / 60)
  minutes -= hours * 60
  if seconds == 1:
    second_str = "1 second"
  else:
    second_str = str(seconds) + " seconds"
  if minutes > 0:
    if minutes == 1:
      minute_str = "1 minute"
    else:
      minute_str = str(minutes) + " minutes"
  if hours > 0:
    if hours == 1:
      output = "1 hour"
    else:
      output = str(hours) + " hours"
    if minutes > 0:
      if seconds > 0:
        output += ", " + minute_str + ", and " + second_str
      else:
        output += " and " + minute_str
    else:
      if seconds > 0:
        output += " and " + second_str
  else:
    if minutes > 0:
      if seconds > 0:
        output = minute_str + " and " + second_str
      else:
        output = minute_str
    else:
      output = second_str
  return output
