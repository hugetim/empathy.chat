import datetime
import anvil.tz


CANCEL_MIN_MINUTES = 5
CANCEL_DEFAULT_MINUTES = 15
CANCEL_TEXT = {5: "5 min. prior",
               15: "15 min. prior",
               30: "30 min. prior",
               60: "1 hr. prior",
               120: "2 hrs. prior",
               8*60: "8 hrs. prior",
               24*60: "24 hrs. prior",
               48*60: "48 hrs. prior",
               "custom": "a specific time...",
              }



def get_proposal_errors(proposal):
  pass
