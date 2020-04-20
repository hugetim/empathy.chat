import datetime
import anvil.tz
import math


DURATION_TEXT = {15: "15 min. (5 & 5)",
                 25: "25 min. (10 & 10)",
                 35: "35 min. (15 & 15)",
                 45: "45 min. (20 & 20)",
                 55: "55 min. (25 & 25)",
                 65: "65 min. (30 & 30)"}


def now():
  return datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc())


def seconds_to_digital(seconds):
  original = seconds
  seconds = abs(seconds)
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
  if original < abs(original):
    output = "-" + output
  return output


def seconds_to_words(seconds):
  original = seconds
  seconds = abs(seconds)
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
  if original < abs(original):
    output = "minus " + output
  return output


def re_hours(h, set_time):
  hours = (3600.0*h - (now() - set_time).seconds)/3600.0
  return hours
