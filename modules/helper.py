import datetime
import parameters as p
import anvil.tz

def seconds_left(status, last_confirmed, ping_start=None)
    now = datetime.datetime.now(ref_time.tzinfo)
    if status in ["pinging-mult", "pinging-one", "pinged-mult", "pinged-one"]:
      min_confirm_match = p.CONFIRM_MATCH_SECONDS - (now - ping_start).seconds
      if status=="pinging-mult":
        return min_confirm_match + p.BUFFER_SECONDS
      elif status=="pinged-mult":
        return min_confirm_match
    wait_time = p.WAIT_SECONDS - (now - last_confirmed).seconds
    if status=="pinging-one":
      return max(min_confirm_match, joint_wait_time) + p.BUFFER_SECONDS
    elif status=="pinged-one":
      return max(min_confirm_match, joint_wait_time)
    elif status in ["requesting", "requesting-confirm"]:
      return wait_time
    else:
      print("helper.seconds_left(s,lc,ps): " + status)
