from ._anvil_designer import InviteETemplate
from anvil import *
import anvil.server
from ..... import portable as t
from datetime import timedelta
from ....DashForm.CreateForm import CreateForm


class InviteE(InviteETemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.

  def not_now_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.parent.raise_event("x-close-alert", value=True)  

  def propose_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    state = anvil.server.call('get_status')
    top_form = get_open_form()
    top_form.reset_status(state)
    if state['status'] not in ["pinging", "matched"]:
      top_form.content.propose(link_key=self.item['link_key'])
    else:
      alert("Unable to propose exchange just now. Please try again later.")
    self.parent.raise_event("x-close-alert", value=True) 
#     self.linear_panel_1.visible = False
#     new_prop = t.Proposal(times=[t.ProposalTime(start_now=False)])
#     form_item = new_prop.create_form_item("now not allowed",
#                                           self.get_conflict_checks())
#     form_item['eligible'] = 0
#     form_item['eligible_users'] = []
#     form_item['user_items'] = []
#     self.create_form = CreateForm(item=form_item)
#     get_open_form().proposal_alert = self.create_form
#     self.create_form.add_event_handler("x-close-alert", self.close_create_form)
#     self.add_component(self.create_form)

#   def close_create_form(self, value, **event_args):
#     if value is True:
#       anvil.server.call('add_invite_proposal', self.item['link_key'], self.create_form.item)
#       self.parent.raise_event("x-close-alert", value=True)
#     else:
#       self.create_form.remove_from_parent()
#       self.linear_panel_1.visible = True

#   def get_conflict_checks(self):
#     proposals, upcomings = anvil.server.call('get_proposals_upcomings')
#     conflict_checks = [{'start': match_dict['start_date'],
#                         'end': (match_dict['start_date']
#                                 + timedelta(minutes=match_dict['duration_minutes']))} 
#                        for match_dict in upcomings]
#     for port_prop in t.Proposal.props_from_view_items(proposals):
#       conflict_checks += port_prop.get_check_items()
