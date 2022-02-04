import anvil.server
from . import glob
from . import helper as h


def get_urls():
  return anvil.server.call('get_urls', ['nycnvc_feelings_needs',
                                        'doorbell_mp3',
                                        'doorbell_wav',
                                        'bowl_struck_wav',
                                       ])

  
def init_pending_exchange(status):
  proptime_id, jitsi_code, duration, my_slider_value = (
    anvil.server.call('init_match_form')
  )
  return ExchangeState(status=status,
                      proptime_id=proptime_id,
                      jitsi_code=jitsi_code,
                      duration=duration,
                      my_slider_value=my_slider_value,
                     )


def slider_value_missing(value):
  return type(value) == str

  
class PendingState(h.AttributeToKey):
  def __init__(self, status, proptime_id, jitsi_code, duration, my_slider_value="", jitsi_domain="meet.jit.si", how_empathy_list=None):
    self.status = status
    self.proptime_id = proptime_id
    self.jitsi_code = jitsi_code
    self.jitsi_domain = jitsi_domain
    self.duration = duration
    self.my_slider_value = my_slider_value
    self.how_empathy_list = how_empathy_list if how_empathy_list else []

  @property
  def default_timer_minutes(self):
    return (self.duration - 5)/2
  
  @property 
  def jitsi_url(self):
    """Initialize or destroy embedded Jitsi Meet instance"""
    # https://jitsi.github.io/handbook/docs/user-guide/user-guide-advanced
    base = f"https://{self.jitsi_domain}/" #if p.DEBUG_MODE else "https://8x8.vc/vpaas-magic-cookie-848c456481fc4755aeb61d02b9d9dab2/"
    return base + self.jitsi_code + "#config.prejoinPageEnabled=false"    
 
  @property
  def slider_status(self):
    return "waiting"

  def start_exchange(self):
    state = anvil.server.call('match_commit')
    self.status = state['status']


class ExchangeState(PendingState):
  def __init__(self, message_items=None, their_slider_value="", their_external=False, their_complete=False, their_name="", **kwargs):
    super().__init__(**kwargs)
    self.their_slider_value = their_slider_value
    self.their_external = their_external
    self.their_complete = their_complete
    self.their_name = their_name
    self.message_items = message_items if message_items else []

  @property
  def slider_status(self):
    if self.status != "matched":
      return super().slider_status
    elif slider_value_missing(self.my_slider_value):
      return None
    else:
      return "submitted" if slider_value_missing(self.their_slider_value) else "received"

  def exit(self):
    if self.status == "matched":
      anvil.server.call('match_complete')
    else:
      anvil.server.call('cancel_now', self.proptime_id)  

  def add_chat_message(self, message):
    new_match_state = anvil.server.call('add_chat_message', message=message)
    for key, value in new_match_state.items():
      setattr(self, key, value)

  @property
  def messages_plus(self):
    out = []
    for i, how_empathy in enumerate(self.how_empathy_list):
      if how_empathy:
        mine = i == 0
        who = glob.name if mine else self.their_name
        out.append({
          "label": f"[from {who}'s profile]",
          "message": f"How {who} likes to receive empathy:\n{how_empathy}",
          "me": mine,
        })
    first_message = {True: True, False: True}
    for message in self.message_items:
      mine = message['me']
      if first_message[mine]:
        message['label'] = glob.name if mine else self.item.their_name
        first_message[mine] = False
    out += self.message_items
    return out


def update_exchange_state(previous_state):
  state_dict = previous_state.__dict__
  state_dict.update(anvil.server.call_s('update_match_form'))
  return ExchangeState(**state_dict)


def submit_slider(value):
  return anvil.server.call('submit_slider', value)


def update_my_external(value):   
  anvil.server.call_s('update_my_external', value)
  