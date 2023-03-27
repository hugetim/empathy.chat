import anvil.server as server
from . import glob
from . import helper as h


def get_urls():
  return server.call_s('get_urls', ['nycnvc_feelings_needs',
                                    'doorbell_mp3',
                                    'doorbell_wav',
                                    'bowl_struck_wav',
                                   ])

  
def slider_value_missing(value):
  return value is None


def submit_slider(value):
  return server.call('submit_slider', value)


def update_my_external(value):   
  server.call_s('update_my_external', value)

  
class PendingState(h.AttributeToKey):
  def __init__(self, status, proptime_id, jitsi_code, duration, my_slider_value=None, jitsi_domain="meet.jit.si", how_empathy_list=None):
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
  
  def __init__(self, message_items=None, their_slider_value=None, their_external=None, their_complete=None, their_name="", **kwargs):
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
      server.call('match_complete')
    else:
      server.call('cancel_now', self.proptime_id)
    for channel in self.channels:
      glob.publisher.close_channel(channel)

  def add_chat_message(self, message):
    new_match_state = server.call('add_chat_message', message=message)
    for key, value in new_match_state.items():
      setattr(self, key, value)

  @property
  def messages_plus(self):
    out = [] #self._format_how_empathy_as_messages()
    self._label_first_messages_with_name()
    out += self.message_items
    return h.add_new_day_to_message_list(out)

  @property
  def how_empathy_items(self):
    if self.how_empathy_list and (self.how_empathy_list[0] or self.how_empathy_list[1]):
      return [(self.their_name, self.how_empathy_list[1]),
              (f"{glob.name} (me)", self.how_empathy_list[0])]
    else:
      return []
  
  def _format_how_empathy_as_messages(self):
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
    return out

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
    if self.how_empathy_list != prev.how_empathy_list:
      glob.publisher.publish("match.update_how", "new_how_empathy")

  @staticmethod
  def initialized_state(status):
    proptime_id, jitsi_code, duration, my_slider_value = (
      server.call('init_match_form')
    )
    return ExchangeState(status=status,
                         proptime_id=proptime_id,
                         jitsi_code=jitsi_code,
                         duration=duration,
                         my_slider_value=my_slider_value,
                        )
  