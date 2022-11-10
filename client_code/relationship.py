from anvil.server import portable_class


UNLINKED = 99


@portable_class
class Relationship:
  LAST_NAME_NOTE = ("Only your direct phone buddies and group hosts (and members of any groups you host) will be able to see your full last name. "
                    "Otherwise, only 2nd degree connections (that is, phone buddies of phone buddies, or equivalent) will be able to see your last initial."
                   )
  PROFILE_URL_NOTE = "Only phone buddies are allowed to see this profile URL, aside from the empathy.chat admin."
  
  def __init__(self, distance=UNLINKED, degree=UNLINKED, group_host_to_member=False):
    self.distance = distance
    self.degree = degree if degree < UNLINKED else distance
    self.group_host_to_member = group_host_to_member
    
  def __repr__(self):
    return f"Relationship({self.distance}, {self.degree}, {self.group_host_to_member})"
    
  @property
  def last_name_visible(self):
    return self.distance <= 1 or self.group_host_to_member
    
  @property
  def last_initial_visible(self):
    return self.distance <= 2 or self.last_name_visible
  
  @property
  def profile_url_visible(self):
    return self.distance <= 1
