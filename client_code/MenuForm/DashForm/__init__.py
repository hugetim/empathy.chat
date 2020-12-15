from ._anvil_designer import DashFormTemplate
from anvil import *
import anvil.server
from .CreateForm import CreateForm
from ... import timeproposals as t


class DashForm(DashFormTemplate):
  def __init__(self, name, tallies, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
    
    if name:
      self.welcome_label.text = "Hi, " + name + "!"
    self.tallies = tallies
    self.timer_2.interval = 5
       
  def form_show(self, **event_args):
    """This method is called when the HTML panel is shown on the screen"""
    self.top_form = get_open_form()
    self.update_tally_label()

  def timer_2_tick(self, **event_args):
    """This method is called every 5 seconds, checking for status changes"""
    # Run this code approx. once a second
    self.tallies = anvil.server.call_s('get_tallies')
    self.update_tally_label()    
    
  def update_tally_label(self):
    """Update form based on tallies state"""
    pass

  def tally_text(self, tallies):
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
    
  def propose_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    content = CreateForm(item=CreateForm.proposal_to_item(t.DEFAULT_PROPOSAL))
    self.top_form.proposal_alert = content
    out = alert(content=self.top_form.proposal_alert,
                title="New Empathy Chat Proposal",
                large=True,
                dismissible=False,
                buttons=[])
    if out is True:
      if content.item['start_now']:
        s, sl, num_emailed = anvil.server.call('add_request', self.request_type)
        self.top_form.set_seconds_left(s, sl)
        self.top_form.reset_status()
