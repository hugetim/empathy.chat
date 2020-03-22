from .MenuForm.DashForm import DashForm
from .MenuForm.WaitForm import WaitForm
from .MenuForm.MatchForm import MatchForm


def go_dash(top_form):
  content = DashForm(top_form.name,
                     top_form.drop_down_1_items, 
                     top_form.request_type, 
                     top_form.tallies)
  top_form.load_component(content)
 

def go_match(top_form):
  top_form.test_link.visible = False
  content = MatchForm(top_form.drop_down_1_items, 
                      top_form.request_type)
  top_form.load_component(content)