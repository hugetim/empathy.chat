import anvil.google.auth, anvil.google.drive
import datetime
import anvil.tz
import math


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
    output = "-" + output
  return output


def re_hours(h, set_time):
  hours = (3600.0*h - (now() - set_time).seconds)/3600.0
  return hours


def tally_text(tallies):
  text = ""
  if tallies['receive_first'] > 1:
    if tallies['will_offer_first'] > 0:
      text = ('There are currently '
              + str(tallies['receive_first'] + tallies['will_offer_first'])
              + ' others requesting an empathy exchange. Some are '
              + 'requesting a match with someone willing to offer empathy first.')
    else:
      assert tallies['will_offer_first'] == 0
      text = ('There are currently '
              + str(tallies['receive_first'])
              + ' others requesting matches with someone willing to offer empathy first.')
  elif tallies['receive_first'] == 1:
    if tallies['will_offer_first'] > 0:
      text = ('There are currently '
              + str(tallies['receive_first'] + tallies['will_offer_first'])
              + ' others requesting an empathy exchange. '
              + 'One is requesting a match with someone willing to offer empathy first.')
    else:
      assert tallies['will_offer_first'] == 0
      text = 'There is one person currently requesting a match with someone willing to offer empathy first.'
  else:
    assert tallies['receive_first'] == 0
    if tallies['will_offer_first'] > 1:
      text = ('There are currently '
              + str(tallies['will_offer_first'])
              + ' others requesting an empathy exchange, '
              + 'all of whom are willing to offer empathy first.')
    elif tallies['will_offer_first'] == 1:
      text = ('There is one'
              + ' person currently requesting an empathy exchange, '
              + 'willing to offer empathy first.')
    else:
      assert tallies['will_offer_first'] == 0
  if tallies['will_offer_first'] == 0:
    if tallies['receive_first'] > 0:
      if tallies['request_em'] > 1:
        text += (str(tallies['request_em'])
                 + ' others are currently receiving email notifications '
                 + 'about each request for empathy.')
      elif tallies['request_em'] == 1:
        text += ('One other person is currently receiving email notifications '
                 + 'about each request for empathy.')
    else:
      if tallies['request_em'] > 1:
        text += (str(tallies['request_em'])
                 + ' people are currently receiving email notifications '
                 + 'about each request for empathy.')
      elif tallies['request_em'] == 1:
        text += ('One person is currently receiving email notifications '
                 + 'about each request for empathy.')
  return text
