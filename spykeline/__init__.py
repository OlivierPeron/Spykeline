import os
import subprocess

spykeparams = None

def set_spykeparams(gui_params):
    spykeparams = gui_params



# Export the set_params function and params
__all__ = ['set_spykeparams', 'spykeparams']