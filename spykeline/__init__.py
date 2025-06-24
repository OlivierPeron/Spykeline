import os
import subprocess

from .config import default_parameters

spykeparams = default_parameters

def set_spykeparams(gui_params):
    global spykeparams
    spykeparams = gui_params
    return spykeparams

from .tools import define_paths, read_rhd, phy_export, load_data
from .preprocessing import *
from .spikesorting import *
from .curation import *