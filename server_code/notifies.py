from anvil import secrets
import anvil.email
import anvil.server
from . import server_misc as sm
from . import accounts
from . import parameters as p
from . import helper as h
from . import portable as port
from anvil_extras.server_utils import timed

  
def email_send(to_user, subject, text, from_name="", from_address="no-reply"):
  return anvil.email.send(
    from_name=from_name if from_name else _from_name_for_email(),
    to=to_user['email'],
    subject=subject,
    text=text
  )


def send_sms(to_number, text):
  account_sid = secrets.get_secret('account_sid')
  auth_token = secrets.get_secret('auth_token')
  from twilio.rest import Client
  client = Client(account_sid, auth_token)
  try:
    message = client.messages.create(
      body=text,
      from_='+12312905138',
      to=to_number,
    )
    print(f"send_sms sid, {message.sid}")
    return None
  except Exception as exc:
    sm.warning(f"Handled: {repr(exc)}")
    return str(exc)
  

def _addressee_name(user):
  name = user['first_name']
  return name if name else "empathy.chat user"


def _other_name(name=""):
  return name if name else "Another empathy.chat user"


def _names(other_users, to_user, name_fn=sm.name):
  return h.series_str([name_fn(u, to_user=to_user) for u in other_users])
  

def _from_name_for_email(name=""):
  return f"empathy.chat (for {name})" if name else "empathy.chat"


def _email_unsubscribe(detail='click the pencil button beneath "Email me (if not already notified by Text/SMS) for chats proposed/initiated by:", uncheck all boxes, and click "OK"'):
  return f'To unsubscribe: Login to empathy.chat, go to Settings, {detail}.'


def when_str(start, user):
  if start:
    start_user_tz = sm.as_user_tz(start, user)
    now_user_tz = sm.as_user_tz(sm.now(), user)
    if start_user_tz.date() == now_user_tz.date():
      out = f"today at {h.time_str(start_user_tz)}"
    else:
      out = h.day_time_str(start_user_tz)
    seconds_away = (start-sm.now()).total_seconds()
    if seconds_away < 60*15 and seconds_away > 0:
      time_in_words = h.seconds_to_words(seconds_away, include_seconds=False)
      out += f" (in {time_in_words})"      
    return out
  else: 
    return "now"  


def _duration_start_str(request_info, user):
  out = port.DURATION_TEXT[request_info.duration]
  if request_info.start_now:
    out += ", starting now"
  else:
    out += f", {when_str(request_info.start_dt, user)}"
  return out


@sm.background_task_with_reporting
def pings(user_ids, start, duration):
  for user_id in user_ids:
    user = sm.get_other_user(user_id)
    ping(user, start, duration)
  

@sm.background_task_with_reporting
def ping(user, start, duration):
  """Notify pinged user (or proposer of fully accepted "later" request)"""
  print(f"'ping', {start}, {duration}")
  subject = "empathy.chat - request accepted"
  content1 = f"Your request for a {duration} minute empathy chat, starting {when_str(start, user)}, has been accepted."
  content2 = f"Go to {p.URL} for the empathy chat."
  if user['phone'] and user['notif_settings'].get('essential') == 'sms':
    send_sms(sm.phone(user), f"{subject}: {content1} {content2}")
  elif user['notif_settings'].get('essential'):  # includes case of 'sms' and not user['phone']
    email_send(
      to_user=user,
      subject=subject,
      text=f'''Dear {_addressee_name(user)},

{content1}

{content2}
'''
    )
  #p.s. You are receiving this email because you checked the box: "Notify me by email when a match is found." To stop receiving these emails, ensure this option is unchecked when requesting empathy.


def notify_match_cancel_bg(user, start, canceler_name=""):
  anvil.server.launch_background_task('notify_match_cancel', user, start, canceler_name)


@sm.background_task_with_reporting
def notify_match_cancel(user, start, canceler_name=""):
  """Notify cancelled-on user"""
  print(f"'notify_match_cancel', {start}, {canceler_name}")
  subject = "empathy.chat - upcoming match cancelled"
  content = f"{_other_name(canceler_name)} has cancelled your empathy chat, previously scheduled to start {when_str(start, user)}."
  if user['phone'] and user['notif_settings'].get('essential') == 'sms':
    send_sms(sm.phone(user), f"{subject}: {content}")
  elif user['notif_settings'].get('essential'):  # includes case of 'sms' and not user['phone']
    email_send(
      to_user=user,
      from_name=_from_name_for_email(canceler_name),
      subject=subject,
      text=f'''Dear {_addressee_name(user)},

{content}
''')

    
def notify_late_for_chat(user, start, waiting_users=[]):
  """Notify late user"""
  print(f"'notify_late_for_chat', {start}")
  subject = "empathy.chat - late for scheduled chat"
  verb = "is" if len(waiting_users) == 1 else "are"
  participant_names = _names(waiting_users, to_user=user)
  content1 = f"{participant_names} {verb} waiting for you to begin an empathy chat that was scheduled to start {when_str(start, user)}."
  content2 = f"Please login to {p.URL} now."
  if user['phone'] and user['notif_settings'].get('essential') == 'sms':
    send_sms(sm.phone(user), f"{subject}: {content1} {content2}")
  elif user['notif_settings'].get('essential'):  # includes case of 'sms' and not user['phone']
    email_send(
      to_user=user,
      from_name=_from_name_for_email(participant_names),
      subject=subject,
      text=f'''Dear {_addressee_name(user)},

{content1}

{content2}
''')


def notify_requests_cancel(user, requester, title):
  """Notify recipient of cancelled proposal if settings permit"""
  from .request_interactor import is_included
  eligibility_specs = accounts.get_eligibility_specs(user)
  if user['phone'] and eligibility_specs.get('sms') and is_included(eligibility_specs['sms'], requester):
    _notify_requests_cancel_by(user, requester, title, 'sms')
  elif eligibility_specs.get('email') and is_included(eligibility_specs['email'], requester):
    _notify_requests_cancel_by(user, requester, title, 'email')


def _notify_requests_cancel_by(user, requester, title, medium):
  print(f"'_notify_requests_cancel_by', {user['email']}, {title}, {medium}")
  requester_name = sm.name(requester, to_user=user)
  subject = f"empathy.chat - {title}"
  content1 = f"{_other_name(requester_name)} has cancelled their empathy chat request."
  if medium == 'sms':
    send_sms(sm.phone(user), f"empathy.chat: {content1}")
  elif medium == 'email':
    email_send(
      to_user=user,
      from_name=_from_name_for_email(requester_name),
      subject=f"{subject} from {requester_name}",
      text=f'''Dear {_addressee_name(user)},

{content1}

{_email_unsubscribe()}
''')


def notify_requests(user, requester, requests_info, title, desc):
  """Notify recipient of added/edited requests if settings permit"""
  from .request_interactor import is_included
  eligibility_specs = accounts.get_eligibility_specs(user)
  if user['phone'] and eligibility_specs.get('sms') and is_included(eligibility_specs['sms'], requester):
    _notify_requests_by(user, requester, requests_info, title, desc, 'sms')
  elif eligibility_specs.get('email') and is_included(eligibility_specs['email'], requester):
    _notify_requests_by(user, requester, requests_info, title, desc, 'email')


def _notify_requests_by(user, requester, requests_info, title, desc, medium):
  print(f"'_notify_requests_by', {user['email']}, {next(iter(requests_info)).start_dt}, {title}, {desc}, {medium}")
  requester_name = sm.name(requester, to_user=user)
  subject = f"empathy.chat - {title}"
  if len(requests_info) > 1:
    times_str = "\n" + "either " + "\n or ".join([_duration_start_str(info, user) for info in requests_info])
    content2 = f"Login to {p.URL} to accept one."
  else:
    times_str = "\n " + _duration_start_str(next(iter(requests_info)), user)
    content2 = f"Login to {p.URL} to accept."
  content1 = f"{_other_name(requester_name)}{desc}{times_str}."
  if medium == 'sms':
    send_sms(sm.phone(user), f"empathy.chat: {content1}\n{content2}")
  elif medium == 'email':
    email_send(
      to_user=user,
      from_name=_from_name_for_email(requester_name),
      subject=f"{subject} from {requester_name}",
      text=f'''Dear {_addressee_name(user)},

{content1}

{content2}

{_email_unsubscribe()}
''')


def notify_message(user, from_name=""):
  """Notify messaged user"""
  print(f"'_notify_message', {user.get_id()}, {from_name}")
  subject = f"empathy.chat - {_other_name(from_name)} sent you a message"
  content = f"{_other_name(from_name)} has sent you a message on {p.URL}"
  if user['phone'] and user['notif_settings'].get('message') == 'sms':
    send_sms(sm.phone(user), f"empathy.chat - {content}")
  elif user['notif_settings'].get('message'): # includes case of 'sms' and not user['phone']
    email_send(
      to_user=user,
      from_name=_from_name_for_email(from_name),
      subject=subject,
      text=f'''Dear {_addressee_name(user)},

{content}

{_email_unsubscribe("and select 'none' in the drop-down next to 'when someone sends me a message'")}
'''
    ) #dup01
