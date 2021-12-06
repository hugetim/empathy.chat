import anvil.facebook.auth
import anvil.users
import anvil.server
import datetime
import random


quotes = ["We need to receive empathy to give empathy.",
          "Don't just do something, be there.",
          "Postpone result/solution thinking until later; it's through connection that solutions materialize.",
          "Empathy allows us to re-perceive our world in a new way and move forward.",
          "Always listen to what people need rather than what they are thinking about us.",
          "Our goal is to create a quality of empathic connection that allows everyone’s needs to be met.",
          "People heal from their pain when they have an authentic connection with another human being.",
          "Your presence is the most precious gift you can give to another human being.",
          "Empathy lies in our ability to be present without opinion.",
          "Empathy is a respectful understanding of what others are experiencing.",
          ("Instead of offering empathy, we often have a strong urge to give advice "
           + "or reassurance and to explain our own position or feeling. "
           + "Empathy, however, calls upon us to empty our mind and listen to others with our whole being."),
          "The most important use of NVC may be in developing self-compassion.",
         ]

outtakes = ["It may be most difficult to empathize with those we are closest to.",
            "When people are upset, they often need empathy before they can hear what is being said to them.",
            "The ability to offer empathy to people in stressful situations can defuse potential violence.",
           ]

def quote_of_the_day(date):
  random.seed(date.toordinal())
  return f'''"{random.choice(quotes)}"'''
#- Marshall B. Rosenberg'''
