from .MenuForm.DashForm import DashForm
from .MenuForm.WaitForm import WaitForm
from .MenuForm.MatchForm import MatchForm


def go_dash(top_form):
  top_form.test_link.visible = True 
  content = DashForm(top_form.name,
                     top_form.tallies)
  top_form.load_component(content)
  
 
def go_match(top_form):
  top_form.test_link.visible = False
  content = MatchForm()
  top_form.load_component(content)
  
  
def go_wait(top_form):
  top_form.test_link.visible = False
  content = WaitForm(top_form.pinged_em_checked)
  top_form.load_component(content)