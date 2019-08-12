import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import datetime
import parameters as p
import anvil.tz
import math


def now():
  return datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc())


def seconds_left(status, last_confirmed, ping_start=None):
  if status in ["pinging", "pinged"]:
    if ping_start:
      confirm_match = p.CONFIRM_MATCH_SECONDS - (now() - ping_start).seconds
    else:
      confirm_match = p.CONFIRM_MATCH_SECONDS
    if status == "pinging":
      return confirm_match + 2*p.BUFFER_SECONDS # accounts for delay in response arriving
    elif status == "pinged":
      return confirm_match + p.BUFFER_SECONDS # accounts for delay in ping arriving
  elif status == "requesting":
    if last_confirmed:
      return p.WAIT_SECONDS - (now() - last_confirmed).seconds
    else:
      return p.WAIT_SECONDS
  else:
    print("helper.seconds_left(s,lc,ps): " + status)


def seconds_to_digital(seconds):
  minutes = math.trunc(seconds / 60)
  seconds = int(seconds - minutes * 60)
  hours = math.trunc(minutes / 60)
  minutes = int(minutes - hours * 60)
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
  minutes = math.trunc(seconds / 60)
  seconds = int(seconds - minutes * 60)
  hours = math.trunc(minutes / 60)
  minutes = int(minutes - hours * 60)
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


def re_hours(h, set_time):
  print (h, set_time)
  hours = (3600.0*h - (now() - set_time).seconds)/3600.0
  print hours
  return hours
