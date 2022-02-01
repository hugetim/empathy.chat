import anvil.users
import anvil.server
import anvil.tables
from anvil.tables import app_tables, order_by
import anvil.google.auth
import anvil.tables.query as q
import anvil.secrets
import anvil.email
from . import server_misc as sm
from . import parameters as p
from . import helper as h
from anvil_extras.server_utils import timed

  
def email_send(to_user, subject, text, from_name="", from_address="no-reply"):
  return anvil.email.send(
    from_name=from_name if from_name else _from_name_for_email(),
    to=to_user['email'],
    subject=subject,
    text=text
  )


def send_sms(to_number, text):
  account_sid = anvil.secrets.get_secret('account_sid')
  auth_token = anvil.secrets.get_secret('auth_token')
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


def _other_name(name):
  return name if name else "Another empathy.chat user"


def _from_name_for_email(name=""):
  return f"empathy.chat (for {name})" if name else "empathy.chat"


def notify_when(start, user):
  if start:
    start_user_tz = sm.as_user_tz(start, user)
    now_user_tz = sm.as_user_tz(now(), user)
    if start_user_tz.date() == now_user_tz.date():
      out = f"today at {h.time_str(start_user_tz)}"
    else:
      out = h.day_time_str(start_user_tz)
    seconds_away = (start-now()).total_seconds()
    if seconds_away < 60*15:
      time_in_words = h.seconds_to_words(seconds_away, include_seconds=False)
      out += f" (in {time_in_words})"
    return out
  else: 
    return "now"  
  
  
def ping(user, start, duration):
  """Notify pinged user"""
  print(f"'ping', {start}, {duration}")
  subject = "empathy.chat - match confirmed"
  content1 = f"Your proposal for a {duration} minute empathy match, starting {notify_when(start, user)}, has been accepted."
  content2 = f"Go to {p.URL}for the empathy chat."
  if user['phone'] and user['notif_settings'].get('essential') == 'sms':
    send_sms(user['phone'], f"{subject}: {content1} {content2}")
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

  
def notify_match_cancel(user, start, canceler_name=""):
  """Notify canceled-on user"""
  print(f"'notify_match_cancel', {start}, {canceler_name}")
  subject = "empathy.chat - upcoming match canceled"
  content = f"{_other_name(canceler_name)} has canceled your empathy chat, previously scheduled to start {notify_when(start, user)}."
  if user['phone'] and user['notif_settings'].get('essential') == 'sms':
    send_sms(user['phone'], f"{subject}: {content}")
  elif user['notif_settings'].get('essential'):  # includes case of 'sms' and not user['phone']
    email_send(
      to_user=user,
      from_name=_from_name_for_email(canceler_name),
      subject=subject,
      text=f'''Dear {_addressee_name(user)},

{content}
''')
  
      
def notify_proposal_cancel(user, proposal, title, notif_settings_type="specific"):
  """Notify recipient of cancelled specific proposal"""
  print(f"'notify_proposal_cancel', {user['email']}, {proposal.get_id()}, {title}")
  from .proposals import ProposalTime
  proposer_name = name(proposal.proposer, to_user=user)
  subject = f"empathy.chat - {title} from {proposer_name}"
  content1 = f"{_other_name(proposer_name)} has canceled their empathy chat request directed specifically to you."
  if user['phone'] and user['notif_settings'].get(notif_settings_type) == 'sms':
    send_sms(user['phone'], f"{subject}: {content1}")
  elif user['notif_settings'].get(notif_settings_type):  # includes case of 'sms' and not user['phone']
    email_send(
      to_user=user,
      from_name=_from_name_for_email(proposer_name),
      subject=subject,
      text=f'''Dear {_addressee_name(user)},

{content1}
''')

    
def notify_proposal(user, proposal, title, desc, notif_settings_type="specific"):
  """Notify recipient of specific proposal"""
  print(f"'notify_proposal', {user['email']}, {proposal.get_id()}, {title}, {desc}")
  from .proposals import ProposalTime
  proposer_name = name(proposal.proposer, to_user=user)
  subject = f"empathy.chat - {title} from {proposer_name}"
  proptimes = list(ProposalTime.times_from_proposal(proposal, require_current=True))
  if len(proptimes) > 1:
    times_str = "\n" + "either " + "\n or ".join([pt.duration_start_str(user) for pt in proptimes])
    content2 = f"Login to {p.URL} to accept one."
  else:
    times_str = "\n " + proptimes[0].duration_start_str(user)
    content2 = f"Login to {p.URL} to accept."
  content1 = f"{_other_name(proposer_name)}{desc}{times_str}."
  if user['phone'] and user['notif_settings'].get(notif_settings_type) == 'sms':
    send_sms(user['phone'], f"{subject}: {content1} {content2}")
  elif user['notif_settings'].get(notif_settings_type):  # includes case of 'sms' and not user['phone']
    email_send(
      to_user=user,
      from_name=_from_name_for_email(proposer_name),
      subject=subject,
      text=f'''Dear {_addressee_name(user)},

{content1}

{content2}
''')

    
def notify_message(user, from_name=""):
  """Notify messaged user"""
  print(f"'_notify_message', {user.get_id()}, {from_name}")
  subject = f"empathy.chat - {_other_name(from_name)} sent you a message"
  content = f"{_other_name(from_name)} has sent you a message on {p.URL}"
  if user['phone'] and user['notif_settings'].get('message') == 'sms':
    send_sms(user['phone'], f"empathy.chat - {content}")
  elif user['notif_settings'].get('message'): # includes case of 'sms' and not user['phone']
    email_send(
      to_user=user,
      from_name=_from_name_for_email(from_name),
      subject=subject,
      text=f'''Dear {_addressee_name(user)},

{content}
'''
    )

    
# def users_to_email_re_notif(user=None):
#   """Return list of users to email notifications triggered by user

#   Side effect: prune request_em (i.e. switch expired request_em to false)
#   """
#   return []
# import datetime
  #from . import matcher
  #now = now()
  #_prune_request_em()
  #assume_inactive = datetime.timedelta(days=p.ASSUME_INACTIVE_DAYS)
  #min_between = datetime.timedelta(minutes=p.MIN_BETWEEN_R_EM)
  #cutoff_e = now - assume_inactive
  #### comprehension below should probably be converted to loop
  #return [u for u in app_tables.users.search(enabled=True, request_em=True)
  #                if (u['init_date'] > cutoff_e
  #                    and ((not u['last_request_em']) or now > u['last_request_em'] + min_between)
  #                    and u != user
  #                    and c.is_visible(u, user)
  #                    and not matcher.has_status(u))]


# def request_emails(request_type, user):
#   """Email non-active with request_em_check_box checked who logged in recently

#   Non-active means not requesting or matched currently"""
#   if request_type == "receive_first":
#     request_type_text = 'an empathy exchange with someone willing to offer empathy first.'
#   else:
#     assert request_type == "will_offer_first"
#     request_type_text = 'an empathy exchange.'
#   users_to_email = users_to_email_re_notif(user)
#   for u in users_to_email:
#     name = u['name']
#     if not name:
#       name = "empathy.chat user"
#     #anvil.google.mail.send(to=u['email'],
#     #                       subject="empathy.chat - Request active",
#     text=(
# "Dear " + name + ''',

# Someone has requested ''' + request_type_text + '''

# Return to ''' + p.URL + ''' and request empathy to be connected for an empathy exchange (if you are first to do so).

# Thanks!
# Tim
# empathy.chat

# p.s. You are receiving this email because you checked the box: "Notify me of requests by email." To stop receiving these emails, return to the link above and change this setting.
# ''')
#   return len(users_to_email)    