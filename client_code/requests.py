import anvil.server
import anvil.users
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


@anvil.server.portable_class 
class MyRequest(h.PortItem, h.AttributeToKey):
  pass
  def get_errors(self, conflict_checks=None):
    """Return a dictionary of errors
    >>>(ProposalTime(start_now=False, start_date= h.now()).get_errors()
        == {'start_date': ("The Start Time must be at least " 
                          + str(CANCEL_MIN_MINUTES) + " minutes away.")}
    True
    """
    now = h.now()
    messages = {}
    if self.start_date:
      if self.start_date < (now + datetime.timedelta(minutes=CANCEL_MIN_MINUTES)):
        messages['start_date'] = ("The Start Time must be at least " 
                                  + str(CANCEL_MIN_MINUTES) + " minutes away.")
      else:
        if self.expire_date < now:
          messages['cancel_buffer'] = 'The specified "Cancel" time has already passed.'
        elif self.expire_date > self.start_date:
          messages['cancel_buffer'] = ('The "Cancel" time must be prior to the Start Time (by at least '
                                      + str(CANCEL_MIN_MINUTES) + ' minutes).')
        elif self.expire_date > (self.start_date 
                                 - datetime.timedelta(minutes=CANCEL_MIN_MINUTES)):
          messages['cancel_buffer'] = ('The "Cancel" time must be at least ' 
                                      + str(CANCEL_MIN_MINUTES) + ' minutes prior to the Start Time.')
    return messages