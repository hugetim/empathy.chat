import anvil.server
import anvil
from . import helper as h


def handle_server_connection_error(err):
  anvil.Notification("Server connection error. If something is not working as expected, please refresh the page.",
                      style="warning", timeout=5).show()
  try:
    h.warning(repr(err))
  except Exception as err_err:
    print(f"error_handler ({repr(err)}) warning exception: {repr(err_err)}")


def report_error(err):
  app_info_dict = {'id': anvil.app.id,
                  'branch': anvil.app.branch,
                  'environment.name': anvil.app.environment.name,
                  }
  anvil.server.call('report_error', repr(err), app_info_dict)