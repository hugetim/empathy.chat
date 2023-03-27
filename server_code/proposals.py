# import anvil.tables
# from anvil.tables import app_tables
# import anvil.tables.query as q
# import anvil.server
# from . import parameters as p
# from . import server_misc as sm
# from . import notifies as n
# from . import portable as port
# from . import helper as h
# from . import groups
# from . import network_interactor as ni
# from anvil_extras.server_utils import timed


# class ProposalTime():
  
#   def __init__(self, proptime_row):
#     self._proptime_row = proptime_row

#   def get_id(self):
#     return self._proptime_row.get_id()  
  
#   def portable(self):
#     row_dict = dict(self._proptime_row)
#     row_dict['time_id'] = self.get_id()
#     users_accepting = row_dict.pop('users_accepting')
#     if users_accepting:
#       row_dict['users_accepting'] = [sm.get_port_user(user) for user in users_accepting]
#     else:
#       row_dict['users_accepting'] = []
# #     if row_dict.pop('current'):
# #       row_dict['status'] = "current"
# #     elif row_dict.pop('cancelled'):
# #       row_dict['status'] = "cancelled"
# #     else:
# #       row_dict['status'] = "hidden"
#     if (not row_dict['current']) or row_dict['cancelled']:
#       sm.warning(f"unexpected m.ProposalTime.portable()")
#     del row_dict['current']
#     del row_dict['cancelled']
#     del row_dict['missed_pings']
#     del row_dict['proposal']
#     del row_dict['fully_accepted']
#     return port.ProposalTime(**row_dict)

#   def __repr__(self):
#     return repr(self.portable())
  
#   @property
#   def _row(self):
#     return self._proptime_row

#   def __getitem__(self, key):
#     return self._proptime_row[key]

#   def __setitem__(self, key, value):
#     self._proptime_row[key] = value
  
#   @property
#   def ping_start(self):
#     return self._proptime_row['accept_date']
 
#   def duration_start_str(self, user):
#     out = port.DURATION_TEXT[self['duration']]
#     if self['start_now']:
#       out += ", starting now"
#     else:
#       out += f", {n.when_str(self['start_date'], user)}"
#     return out

#   def get_match_info(self):
#     return self['jitsi_code'], self['duration']
  
#   @property
#   def proposal(self):
#     return Proposal(self._proptime_row['proposal'])

#   def all_users(self):
#     return [self.proposal.proposer] + list(self['users_accepting'])
  
#   def is_accepted(self):
#     return len(self.all_users()) >= self.proposal['max_size']
  
#   def attempt_accept(self, user, partial_state):
#     """Returns True if ping_needed, None otherwise"""
#     if sm.DEBUG:
#       print("_attempt_accept_proptime")
#     status = partial_state['status']
#     if (status in [None, "requesting"] 
#         and self['current'] 
#         and (not self['fully_accepted'])
#         and self.proposal.is_visible(user)):
#       return self.accept(user, status)
   
#   def accept(self, user, status):
#     """Returns True if ping_needed, None otherwise"""
#     if sm.DEBUG:
#       print("accept_proptime")
#     self._cancel_any_conflicting_own_now_proposal(user, status)
#     self['users_accepting'] += [user]
#     if self.is_accepted():
#       return self._register_fully_accepted(user)

#   def _register_fully_accepted(self, user):
#     """Returns True if ping_needed, None otherwise"""
#     from . import matcher as m
#     now = sm.now()
#     self['fully_accepted'] = True
#     self['accept_date'] = now
#     self.proposal.hide_unaccepted_times()
#     if not self['start_now']:
#       return m.commit_proptime_to_match(self, user)
#     elif (now - (self['start_date'])).total_seconds() <= p.BUFFER_SECONDS:
#       return m.commit_proptime_to_match(self, user)
#     else:
#       return True
  
#   def _cancel_any_conflicting_own_now_proposal(self, user, status):
#     if self['start_now'] and status == "requesting":
#       own_now_proposal_time = ProposalTime.get_now_proposing(user)
#       if own_now_proposal_time:
#         ProposalTime(own_now_proposal_time).proposal.cancel_all_times()

#   def ping(self):
#     anvil.server.launch_background_task(
#       'ping',
#       user=self.proposal.proposer,
#       start=None if self['start_now'] else self['start_date'],
#       duration=self['duration'],
#     )    
      
#   def in_users_accepting(self, user):
#     return self['users_accepting'] and user in self['users_accepting']
      
#   def remove_accepting(self, user=None):
#     # below code assumes only dyads allowed
#     accepting_list = list(self['users_accepting'])
#     accepting_list.remove(user)
#     self['users_accepting'] = accepting_list
#     self['fully_accepted'] = False
#     self['accept_date'] = None
#     if not self['users_accepting']:
#       self.proposal.unhide_times()

#   def cancel_other(self, user):
#     if self.in_users_accepting(user):
#       self.cancel(missed_ping=1)
#     elif self.proposal.proposer == user:
#       # below code assumes only dyads allowed
#       self.remove_accepting(user)
#       if self.is_expired():
#         self.cancel()  
    
#   def cancel_this(self, user):
#     if self.in_users_accepting(user):
#       self.remove_accepting(user)
#       if self.is_expired():
#        self.cancel() 
#     elif self.proposal.proposer == user:
#       self.cancel()

#   def is_expired(self):
#     return sm.now() > self['expire_date']

#   def notify_cancel(self):
#     if len(list(ProposalTime.times_from_proposal(self.proposal))) == 1:
#       self.proposal.notify_cancel()
# #     else:
# #       old_port_prop = self.proposal.
# #       self.proposal.notify_edit()
  
#   def cancel_time_only(self, missed_ping=None):
#     if self['fully_accepted']:
#       self.proposal.unhide_times()
#     self['current'] = False
#     self['cancelled'] = True
#     if missed_ping:
#       self['missed_pings'] += 1   
  
#   def cancel(self, missed_ping=None):
#     self.cancel_time_only(missed_ping)
#     self.proposal.cancel_if_no_times() 

#   def hide(self):
#     self['current'] = False

#   def unhide(self):
#     if self['cancelled'] != False:
#       sm.warning(f"self._proptime_row['cancelled'] != False")
#     self['current'] = True
    
#   def confirm_wait(self, start_now=True):
#     import datetime
#     if start_now:
#       self['expire_date'] = sm.now() + datetime.timedelta(seconds=p.WAIT_SECONDS)
      
#   def update(self, port_time):
#     if self['start_now'] and port_time.start_now:
#       pass #self._proptime_row['start_date'] = self._proptime_row['start_date']
#     elif port_time.start_now:
#       self['start_date'] = sm.now()
#     else:
#       self['start_date'] = port_time.start_date
#     self['start_now'] = port_time.start_now # order: after 'start_date' set
#     self['duration'] = port_time.duration
#     if port_time.start_now:
#       self.confirm_wait()
#     else:
#       self['expire_date'] = port_time.expire_date
#     self['current'] = True
#     self['cancelled'] = False
    
#   @staticmethod
#   def add(proposal, port_time):
#     ProposalTime(app_tables.proposal_times.add_row(proposal=proposal._row,
#                                                    start_now=port_time.start_now,
#                                                    start_date=sm.now() if port_time.start_now else port_time.start_date,
#                                                    duration=port_time.duration,
#                                                    expire_date=port_time.expire_date,
#                                                    current=True,
#                                                    cancelled=False,
#                                                    users_accepting=[],
#                                                    fully_accepted=False,
#                                                    jitsi_code=h.new_jitsi_code(),
#                                                    missed_pings=0,
#                                                   )).confirm_wait(port_time.start_now)
  
#   @staticmethod
#   def _return(proptime_row):
#     return ProposalTime(proptime_row) if proptime_row else None
  
#   @staticmethod
#   def get_by_id(time_id):
#     return ProposalTime._return(app_tables.proposal_times.get_by_id(time_id))
  
#   @staticmethod
#   def none_left(prop_row):
#     return len(app_tables.proposal_times.search(cancelled=False, proposal=prop_row))==0

#   @staticmethod
#   def times_from_proposal(proposal, require_current=False):
#     if require_current:
#       for proptime_row in app_tables.proposal_times.search(current=True, 
#                                                            proposal=proposal._row):
#         yield ProposalTime(proptime_row)
#     else:
#       for proptime_row in app_tables.proposal_times.search(cancelled=False, 
#                                                            proposal=proposal._row):
#         yield ProposalTime(proptime_row)

#   @staticmethod
#   def get_now(user):
#     current_proptime = ProposalTime.get_now_proposing(user)
#     if not current_proptime:
#       current_proptime = ProposalTime.get_now_accepting(user)
#     return current_proptime
    
#   @staticmethod
#   def get_now_proposing(user):
#     """Return user's current 'start_now' proposal_times row"""
#     if sm.DEBUG:
#       print("get_now_proposal_time")
#     current_prop_rows = Proposal._get_current_prop_rows(user)
#     for prop_row in current_prop_rows:
#       trial_get = app_tables.proposal_times.get(proposal=prop_row,
#                                                 current=True,
#                                                 start_now=True,
#                                                )
#       if trial_get:
#         return ProposalTime(trial_get)
#     return None

#   @staticmethod
#   def get_now_accepting(user):
#     """Return user's current 'start_now' proposal_times row"""
#     if sm.DEBUG:
#       print("_get_now_accept")
#     proptime_row = app_tables.proposal_times.get(users_accepting=[user],
#                                                  current=True,
#                                                  start_now=True,
#                                                 )
#     return ProposalTime._return(proptime_row)

#   @staticmethod
#   def old_to_prune(now):
#     if sm.DEBUG:
#       print("old_prop_times_to_prune")
#     for row in app_tables.proposal_times.search(cancelled=False, 
#                                                 fully_accepted=False,
#                                                 expire_date=q.less_than(now),
#                                                ):
#       yield ProposalTime(row)
  
#   @staticmethod
#   def old_ping_to_prune(now):
#     import datetime
#     # below (matched separately) ensures that no ping proposal_times left hanging by cancelling only one
#     if sm.DEBUG:
#       print("old_ping_to_prune")
#     timeout = datetime.timedelta(seconds=p.WAIT_SECONDS + p.CONFIRM_MATCH_SECONDS + 2*p.BUFFER_SECONDS)
#     cutoff_r = now - timeout
#     for row in app_tables.proposal_times.search(cancelled=False, 
#                                                 start_now=True,
#                                                 fully_accepted=True,
#                                                 accept_date=q.less_than(cutoff_r),
#                                                 expire_date=q.less_than(cutoff_r),
#                                                ):
#       yield ProposalTime(row)
  
  
# class Proposal():
#   def __init__(self, prop_row):
#     self._prop_row = prop_row

#   def get_id(self):
#     return self._prop_row.get_id()
  
#   def portable(self, user):
#     row_dict = dict(self._prop_row)
#     row_dict['prop_id'] = self.get_id()
#     proposer = row_dict.pop('user')
#     row_dict['own'] = proposer == user
#     row_dict['user'] = sm.get_port_user(proposer, user1=user)
#     row_dict['times'] = [proptime.portable() for proptime
#                          in ProposalTime.times_from_proposal(self, require_current=True)]
#     eligible_users = row_dict.pop('eligible_users')
#     row_dict['eligible_users'] = [sm.get_port_user(u, simple=True, user1=user) for u in eligible_users]
#     eligible_groups = row_dict.pop('eligible_groups')
#     row_dict['eligible_groups'] = [groups.Group(group_row['name'], group_row.get_id()) for group_row in eligible_groups]
#     if not row_dict['current']:
#       sm.warning(f"m.Proposal.portable() called on a not-current Proposal")
#     del row_dict['current']
#     del row_dict['created']
#     del row_dict['last_edited']
#     return port.Proposal(**row_dict)
  
#   def __repr__(self):
#     return repr(self.portable(sm.get_acting_user()))
  
#   @property
#   def _row(self):
#     return self._prop_row

#   def __getitem__(self, key):
#     return self._prop_row[key]

#   def __setitem__(self, key, value):
#     self._prop_row[key] = value
    
#   @property
#   def specific_user_eligible(self):
#     if (self['eligible'] == 0 and len(self['eligible_users']) == 1 
#         and not self['eligible_groups'] and not self['eligible_starred']):
#       return self['eligible_users'][0]
#     else:
#       return None
    
#   @property
#   def proposer(self):
#     return self._prop_row['user']
  
#   def is_visible(self, user, distance=None):
#     from .request_interactor import is_eligible
#     return is_eligible(self, user, distance)

#   def hide_unaccepted_times(self):
#     for proptime in ProposalTime.times_from_proposal(self, require_current=True):
#       if not proptime['fully_accepted']:
#         proptime.hide()

#   def unhide_times(self):
#     for proptime in ProposalTime.times_from_proposal(self):
#       proptime.unhide()  
    
#   def cancel_prop_only(self):
#     self['current'] = False
    
#   def cancel_if_no_times(self):
#     if ProposalTime.none_left(self._prop_row):
#       self.cancel_prop_only()

#   def cancel_all_times(self):
#     if sm.DEBUG:
#       print("cancel_all_times")
#     for proptime in ProposalTime.times_from_proposal(self):
#       proptime.cancel_time_only()
#     self.cancel_prop_only()    

#   def add_to_invite(self, link_key):
#     invite_row = app_tables.invites.get(link_key=link_key, user1=self.proposer, origin=True, current=True)
#     if invite_row:
#       invite_row['proposal'] = self._prop_row
#     else:
#       sm.warning(f"no such invite to add proposal to")

#   def update(self, port_prop):
#     self['current'] = True
#     self.last_edited = sm.now()
#     self['min_size'] = port_prop.min_size
#     self['max_size'] = port_prop.max_size
#     self['eligible'] = port_prop.eligible
#     if self.proposer['trust_level'] < 3:
#       self['eligible'] = min(2, self['eligible'])
#     self['eligible_users'] = [sm.get_other_user(port_user.user_id)
#                               for port_user in port_prop.eligible_users]
#     self['eligible_groups'] = [app_tables.groups.get_by_id(port_group.group_id)
#                                for port_group in port_prop.eligible_groups]
#     self['eligible_starred'] = port_prop.eligible_starred
#     ## First cancel removed rows
#     new_time_ids = [port_time.time_id for port_time in port_prop.times]
#     for proptime in ProposalTime.times_from_proposal(self):
#       if proptime.get_id() not in new_time_ids:
#         proptime.cancel()
#     ## Then update or add
#     for port_time in port_prop.times:
#       if port_time.time_id:
#         ProposalTime.get_by_id(port_time.time_id).update(port_time)
#       else:
#         ProposalTime.add(proposal=self, port_time=port_time)

#   def notify_add(self):
#     anvil.server.launch_background_task('notify_add', self._row)
   
#   def notify_edit(self, port_prop, old_port_prop):
#     anvil.server.launch_background_task('notify_edit', self._row, port_prop, old_port_prop)

#   def notify_cancel(self):
#     anvil.server.launch_background_task('notify_cancel', self._row)
 
#   def _notify_add_to(self, other_user):
#     n.notify_proposal(other_user, self, f"empathy request", " has requested an empathy chat:")

#   def _notify_edit_to(self, other_user):
#     n.notify_proposal(other_user, self, "empathy request", " has changed their empathy chat request to:")
    
#   def _notify_cancel_to(self, other_user):
#     n.notify_proposal_cancel(other_user, self, "empathy request")

#   @staticmethod
#   def add(user, port_prop):
#     now = sm.now()
#     user_rows = [sm.get_other_user(port_user.user_id) for port_user in port_prop.eligible_users]
#     group_rows = [app_tables.groups.get_by_id(port_group.group_id) for port_group in port_prop.eligible_groups]
#     new_prop_row = app_tables.proposals.add_row(user=user,
#                                                 current=True,
#                                                 created=now,
#                                                 last_edited=now,
#                                                 min_size=port_prop.min_size,
#                                                 max_size=port_prop.max_size,                                            
#                                                 eligible=port_prop.eligible,
#                                                 eligible_users=user_rows,
#                                                 eligible_groups=group_rows,
#                                                 eligible_starred=port_prop.eligible_starred,
#                                                )
#     if user['trust_level'] < 3:
#       new_prop_row['eligible'] = min(2, new_prop_row['eligible'])
#     new_proposal = Proposal(new_prop_row)
#     for port_time in port_prop.times:
#       ProposalTime.add(proposal=new_proposal, port_time=port_time)
#     return new_proposal
  
#   @staticmethod
#   def get_by_id(prop_id):
#     prop_row = app_tables.proposals.get_by_id(prop_id)
#     if prop_row:
#       return Proposal(prop_row)
#     else:
#       return None

#   @staticmethod
#   def _get_current_prop_rows(user):
#     return app_tables.proposals.search(user=user, current=True)
  
#   @staticmethod
#   def get_port_view_items(user):
#     port_proposals = Proposal.get_port_proposals(user)
#     return port.Proposal.create_view_items(port_proposals)

#   @staticmethod
#   def get_port_proposals(user):
#     """Return list of port.Proposals visible to user
    
#     Side effects: prune proposals
#     """
#     Proposal.prune_all()
#     port_proposals = []
#     all_prop_rows = app_tables.proposals.search(current=True)
#     all_props = [Proposal(row) for row in all_prop_rows]
#     all_proposers = {prop.proposer for prop in all_props}
#     from . import connections as c
#     distances = c.distances(all_proposers, user)
#     for prop in all_props:
#       if prop.is_visible(user, distances[prop.proposer]):
#         port_proposals.append(prop.portable(user))
#     return port_proposals
  
#   @staticmethod
#   def prune_all():
#     """Prune definitely outdated prop_times, unmatched then matched, then proposals"""
#     if sm.DEBUG:
#       print("_prune_proposals")
#     now = sm.now()
#     proposals_to_check = set()
#     for proptime in ProposalTime.old_to_prune(now):
#       proptime.cancel_time_only()
#       proposals_to_check.add(proptime.proposal)
#     # now proposals, after proposal times so they get removed if all times are
#     for proptime in ProposalTime.old_ping_to_prune(now):
#       proptime.cancel_time_only()
#       proposals_to_check.add(proptime.proposal)
#     for proposal in proposals_to_check:
#       proposal.cancel_if_no_times()


# @sm.background_task_with_reporting
# def notify_add(prop_row):
#   from .request_interactor import all_eligible_users
#   prop = Proposal(prop_row)
#   for other_user in all_eligible_users(prop):
#     prop._notify_add_to(other_user)


# @sm.background_task_with_reporting
# def notify_edit(prop_row, port_prop, old_port_prop):
#   from .request_interactor import all_eligible_users
#   prop = Proposal(prop_row)
#   old_all_eligible_users = all_eligible_users(get_eligibility_spec_from_port(old_port_prop, prop.proposer))
#   new_all_eligible_users = all_eligible_users(get_eligibility_spec_from_port(port_prop, prop.proposer))
#   for other_user in new_all_eligible_users - old_all_eligible_users:
#     prop._notify_add_to(other_user)
#   if port_prop.times_notify_info != old_port_prop.times_notify_info:
#     for other_user in new_all_eligible_users & old_all_eligible_users:
#       prop._notify_edit_to(other_user)
#   for other_user in old_all_eligible_users - new_all_eligible_users:
#     prop._notify_cancel_to(other_user)


# @sm.background_task_with_reporting
# def notify_cancel(prop_row):
#   from .request_interactor import all_eligible_users
#   prop = Proposal(prop_row)
#   for other_user in all_eligible_users(prop):
#     prop._notify_cancel_to(other_user)

      
# def get_eligibility_spec_from_port(port_prop, proposer):
#     spec = {}
#     spec['user'] = proposer
#     spec['eligible'] = port_prop.eligible
#     spec['eligible_starred'] = port_prop.eligible_starred
#     spec['eligible_users'] = [sm.get_other_user(port_user.user_id) for port_user in port_prop.eligible_users]
#     spec['eligible_groups'] = [app_tables.groups.get_by_id(port_group.group_id)
#                                for port_group in port_prop.eligible_groups]
#     return spec
  