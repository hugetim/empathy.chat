import anvil.users
import anvil.server
from . import parameters as p
from . import invites
from . import groups
from anvil.js.window import navigator
import re
mobile_devices = "Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini"


MOBILE = re.search(mobile_devices, navigator.userAgent) is not None
trust_level = 0
name = ""
invites = invites.Invites()
my_groups = groups.MyGroups()
