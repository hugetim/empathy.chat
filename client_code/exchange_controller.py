import anvil.server as server
from . import glob
from . import helper as h


def join_exchange(exchange_id):
  server.call('join_exchange', exchange_id)
  return dict(status="matched")


def get_urls():
  return server.call_s('get_urls', ['nycnvc_feelings_needs',
                                    'doorbell_mp3',
                                    'doorbell_wav',
                                    'bowl_struck_wav',
                                   ])

  
def slider_value_missing(value):
  return value is None


def submit_slider(value):
  their_slider_values = server.call('submit_slider', value)
  h.my_assert(len(their_slider_values) == 1, f"ec.submit_slider assumes dyads only")
  return their_slider_values[0]


def update_my_external(value):   
  server.call_s('update_my_external', value)

  
class PendingState(h.AttributeToKey):
  def __init__(self, status, request_id=None, jitsi_code="", duration=None, my_slider_value=None, jitsi_domain="8x8.vc", my_how_empathy=""):
    self.status = status
    self.request_id = request_id
    self.jitsi_code = jitsi_code
    self.jitsi_domain = jitsi_domain
    self.duration = duration
    self.my_slider_value = my_slider_value
    self.my_how_empathy = ""

  @property
  def default_timer_minutes(self):
    return (self.duration - 5)/2
  
  @property 
  def jitsi_url(self):
    """Initialize or destroy embedded Jitsi Meet instance"""
    # https://jitsi.github.io/handbook/docs/user-guide/user-guide-advanced
    base = f"https://{self.jitsi_domain}/vpaas-magic-cookie-848c456481fc4755aeb61d02b9d9dab2/"
    return base + self.jitsi_code + "#config.prejoinPageEnabled=false"    
 
  @property
  def slider_status(self):
    return "waiting"

  def my_initial_slider_value(self):
    return 5 if slider_value_missing(self.my_slider_value) else self.my_slider_value
  
  def start_exchange(self):
    prev_status = self.status
    state = server.call('match_commence')
    self.status = state['status']
    if self.status != prev_status:
      glob.publisher.publish("match.status", "new_status")


class ExchangeState(PendingState):
  channels = ["match.status", "match.slider", "match.messages", "match.external", "match.complete"]
  
  def __init__(self, message_items=None, them=None, **kwargs):
    super().__init__(**kwargs)
    if them is None:
      them = [dict(slider_value=None, external=None, complete=None, name="", how_empathy="")]
    self.them = them
    self.message_items = message_items if message_items else []

  @property
  def _their(self):
    h.my_assert(len(self.them) == 1, "'their' assumes a dyad")
    return self.them[0]
  
  @property
  def their_slider_value(self):
    return self._their['slider_value']

  @their_slider_value.setter
  def their_slider_value(self, value):
    self._their['slider_value'] = value

  @property
  def their_name(self):
    return self._their['name']    

  @property
  def their_external(self):   
    return self._their['external']
    
  @property
  def their_complete(self):   
    return self._their['complete']

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
      server.call('match_complete')
    elif self.status == "requesting":
      server.call('cancel_now', self.request_id)
    else:
      h.my_assert(self.status == "pinged", "ec.ExchangeState.exit status else")
      server.call('ping_cancel')
    for channel in self.channels:
      glob.publisher.close_channel(channel)

  def add_chat_message(self, message):
    self.message_items += [{'me': True, 'message': message, 'time_stamp': h.now()}]
    glob.publisher.publish("match.messages", "messages_update")
    new_match_state = server.call_s('add_chat_message', message=message)
    for key, value in new_match_state.items():
      setattr(self, key, value)

  @property
  def messages_plus(self):
    out = []
    self._label_first_messages_with_name()
    out += self.message_items
    return h.add_new_day_to_message_list(out)

  @property
  def how_empathy_items(self):
    if self.my_how_empathy or any([o_dict['how_empathy'] for o_dict in self.them]):
      return ([(o_dict['name'], o_dict['how_empathy']) for o_dict in self.them]
              + [(f"{glob.name} (me)", self.my_how_empathy)])
    else:
      return []
  
  def _label_first_messages_with_name(self):
    first_message = {True: True, False: True}
    for message in self.message_items:
      mine = message['me']
      if first_message[mine]:
        message['label'] = glob.name if mine else self.their_name
        first_message[mine] = False

  def update(self):
    state_dict = self.__dict__
    prev = ExchangeState(**state_dict)
    state_dict.update(server.call_s('update_match_form'))
    self = ExchangeState(**state_dict)
    if self.status != prev.status:
      glob.publisher.publish("match.status", "new_status")
    if (self.slider_status != prev.slider_status or self.their_name != prev.their_name):
      glob.publisher.publish("match.slider", "slider_update")
    if len(self.messages_plus) > len(prev.messages_plus):
      glob.publisher.publish("match.messages", "messages_update")
    if bool(self.their_external) != bool(prev.their_external):
      glob.publisher.publish("match.external", "their_external_change")
    if bool(self.their_complete) != bool(prev.their_complete):
      glob.publisher.publish("match.complete", "their_complete_change")
    if self.how_empathy_items != prev.how_empathy_items:
      glob.publisher.publish("match.update_how", "new_how_empathy")

  @staticmethod
  def initialized_state(status):
    init_dict = server.call('init_match_form')
    return ExchangeState(status=status, **init_dict)
  