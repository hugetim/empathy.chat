import anvil.users
import anvil.server
import datetime
import anvil.tz
import math


def now():
  return datetime.datetime.now().replace(tzinfo=anvil.tz.tzlocal())


def not_me(user_id):
  return user_id and user_id != anvil.users.get_user().get_id()


def add_num_suffix(num):
  if num == 0:
    return " me"
  else:
    num_suffix = {1: "st", 2: "nd", 3: "rd"}
    return str(num) + num_suffix.get(num, "th")
  

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


def seconds_to_words(seconds, include_seconds=True):
  original = seconds
  seconds = abs(seconds)
  minutes = math.trunc(seconds / 60)
  seconds = int(seconds - minutes * 60)
  hours = math.trunc(minutes / 60)
  minutes = int(minutes - hours * 60)
  days = math.trunc(hours / 24)
  hours = int(hours - days * 24)
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
      if include_seconds and seconds > 0:
        output += ", " + minute_str + ", and " + second_str
      else:
        output += " and " + minute_str
    else:
      if include_seconds and seconds > 0:
        output += " and " + second_str
  else:
    if minutes > 0:
      if include_seconds and seconds > 0:
        output = minute_str + " and " + second_str
      else:
        output = minute_str
    elif include_seconds:
      output = second_str
    else:
      output = "0 minutes"
  if days > 0:
    output = str(days) + (" days, " if days > 1 else " day, ") + output
  if original < abs(original):
    output = "minus " + output
  return output


def re_hours(h, set_time):
  hours = (3600.0*h - (now() - set_time).total_seconds())/3600.0
  return hours


def as_local_tz(_datetime):
  return _datetime.astimezone(anvil.tz.tzlocal())


def time_str(_datetime):
  return _datetime.strftime("X%I:%M%p").replace('X0','X').replace('X','')


def dow_date_str(_datetime):
  return _datetime.strftime("%A, %b X%d, %Y").replace('X0','X').replace('X','')


def day_time_str(_datetime):
  return _datetime.strftime("%a, %b X%d X%I:%M%p").replace('X0','X').replace('X','')


def short_date_str(_datetime):
  return _datetime.strftime("X%m/X%d/%Y").replace('X0','X').replace('X','')


def round_up_datetime(dt, minutes_res=15):
  new_minute = (dt.minute // minutes_res + 1) * minutes_res
  new_dt = dt + datetime.timedelta(minutes = new_minute - dt.minute)
  return new_dt.replace(second=0, microsecond=0)
    
  
def warning(warning_str):
  app_info_dict = {'id': anvil.app.id,
                   'branch': anvil.app.branch,
                   'environment.name': anvil.app.environment.name,
                  }
  anvil.server.call('warning', warning_str, app_info_dict)


def my_assert(statement):
  if not statement:
    warning(f"bool({statement}) is not True")
  
  
class reverse_compare:
    def __init__(self, obj):
        self.obj = obj

    def __eq__(self, other):
        return other.obj == self.obj

    def __lt__(self, other):
        return other.obj < self.obj

      
class PausedTimer:
  def __init__(self, timer):
    self.timer = timer
    self.orig_interval = timer.interval
  def __enter__(self):
    self.timer.interval = 0
  def __exit__(self, type, value, tb):
    self.timer.interval = self.orig_interval
    
@anvil.server.portable_class    
class AttributeToKey:
  def __getitem__(self, key):
    try:
      return self.__getattribute__(key)
    except AttributeError:
      raise KeyError(str(key))

  def __setitem__(self, key, item):
    self.__setattr__(key, item)

  def get(self, key, default=None):
    try:
      return self.__getattribute__(key)
    except AttributeError:
      return default

@anvil.server.portable_class    
class PortItem:
  def update(self, new_self):
    for key, value in new_self.__dict__.items():
      setattr(self, key, value)
      
  def __repr__(self):
    return self.repr_desc + str(self.__dict__)
  
  def relay(self, method, kwargs=None):
    if not kwargs:
      kwargs = {}
    new_object = anvil.server.call(self.server_fn_name, self, method, kwargs)
    self.update(new_object)    
    
    
# @anvil.server.portable_class    
# class ItemWrapped(AttributeToKey):
#   def __init__(self, item):
#     self.item = item
 
#   def to_data(self):
#     return self.item

#   def __getattr__(self, key):
#     return self.item[key]
  
#   def get(self, key, default=None):
#     return self.item.get(key, default)
  
#   def __setattr__(self, key, value):
#     self.item[key] = value
