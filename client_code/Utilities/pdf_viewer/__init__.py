from ._anvil_designer import pdf_viewerTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files

class pdf_viewer(pdf_viewerTemplate):
    def __init__(self, url, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)
        self.url = url + "#toolbar=0&navpanes=0&scrollbar=0"

    def form_show(self, **event_args):
        self.call_js('display_pdf', self.url)

