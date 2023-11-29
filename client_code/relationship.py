from anvil.server import portable_class


UNLINKED = 99


@portable_class
class Relationship:
  LAST_NAME_NOTE = ("Only your close connections and group hosts (and members of any groups you host) will be able to see your full last name. "
                    "Otherwise, only 2nd degree connections (that is, close connections of close connections, or equivalent) will be able to see your last initial."
                   )
  PROFILE_URL_NOTE = "Only close connections are allowed to see this profile URL, aside from the empathy.chat admin."
  MAX_PAIR_ELIGIBLE_DISTANCE = 3
  
  def __init__(self, distance=UNLINKED, degree=UNLINKED, min_trust_level=0, group_host_to_member=False, group_authorized=False, group_authorized_pair=False):
    self.distance = distance
    self.degree = degree if degree < UNLINKED else distance
    self.min_trust_level = min_trust_level
    self.group_host_to_member = group_host_to_member
    self.group_authorized = group_authorized
    self.group_authorized_pair = group_authorized_pair    
    
  def __repr__(self):
    return (f"Relationship(distance={self.distance}, degree={self.degree}, min_trust_level={self.min_trust_level}, "
            f"group_host_to_member={self.group_host_to_member}, group_authorized={self.group_authorized}, "
            f"group_authorized_pair={self.group_authorized_pair})")
    
  @property
  def last_name_visible(self):
    return self.distance <= 1 or self.group_host_to_member
    
  @property
  def last_initial_visible(self):
    return self.distance <= 2 or self.last_name_visible
  
  @property
  def profile_url_visible(self):
    return self.distance <= 1

  @property
  def pair_eligible(self):
    return (
      self.group_authorized_pair
      or (self.min_trust_level >= 3 and self.distance <= self.MAX_PAIR_ELIGIBLE_DISTANCE)
      or (self.min_trust_level >= 2 and self.distance <= 2 and self.degree <= 1)
    )

  @property
  def eligible(self):
    return (
      self.pair_eligible
      or self.group_authorized
      or (self.min_trust_level >= 3 and self.distance <= 6) # distance > 3 only via pair_eligible intermediary in exchange_prospect
    )
  
  def update_distance(self, new_distance):
    return Relationship(
      distance=new_distance,
      degree=self.degree,
      min_trust_level=self.min_trust_level,
      group_host_to_member=self.group_host_to_member,
      group_authorized=self.group_authorized,
      group_authorized_pair=self.group_authorized_pair,
    )