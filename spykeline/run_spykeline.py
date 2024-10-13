import os

import spikeinterface.extractors as se

from . import set_spykeparams
from .GUI import SpykelineGUI
from .tools import define_paths, read_xml, open_recording, phy_export, discard_channels
from .preprocessing.preprocess import run_preprocessing
from .spikesorting.sorter_params import sorter_dict
from .spikesorting.sorting import run_sorting
from .curation.curate import run_curation

def run_spykeline(input_path, secondary_path, probe_list):
    """
    Function running the whole pipeline.

    Parameters
    ----------
    input_path : str
        Path to the folder containing Spykeline's input data.
    secondary_path : str
        Path to the secondary folder for output data.

    Returns
    -------
    None
    """

    paths = define_paths(input_path, secondary_path)

    # Checking if the given paths are correct
    assert os.path.exists(paths['xml']), f"No .xml file named '{os.path.basename(paths['xml'])}' in the folder: '{os.path.dirname(paths['xml'])}'. Are you sure you have put it here and named it properly?"
    assert os.path.exists(paths['rhd']), f"No .rhd file named '{os.path.basename(paths['rhd'])}' in the folder: '{os.path.dirname(paths['rhd'])}'. Are you sure you have put it here and named it properly?"
    assert os.path.exists(paths['dat']), f"No .dat file named '{os.path.basename(paths['dat'])}' in the folder: '{os.path.dirname(paths['dat'])}'. Are you sure you have put it here and named it properly?"

    # Setting the groups of channels based on the neuroscope's xml file
    device_architecture = read_xml(paths['xml'])

    # Getting the recording's parameters
    intan_info = se.read_intan(paths['rhd'], '0')

    metadata = {
        "Anatomical_groups": device_architecture[0],
        "Shanks_groups": device_architecture[1],
        "nb_channels": intan_info.get_num_channels(),
        "Probes": probe_list
    }

    # Opening the recording to process
    raw_recording = open_recording(paths['dat'], intan_info)

    # Remove the last channel (accelerometer)
    raw_recording = raw_recording.remove_channels(metadata['Anatomical_groups'][-1])

    metadata['Anatomical_groups'] = metadata['Anatomical_groups'][:-1]
    metadata['Shanks_groups'] = metadata['Shanks_groups'][:-1]

    assert spykeparams['spikesorting']['sorter'] in sorter_dict.keys(), "It seems the sorter you are trying to use isn't available here. Make sure there isn't any typo and that your sorter is within sorter_params!"

    # Preprocessing
    pp_recording = run_preprocessing(raw_recording, paths, metadata)

    pp_recording, metadata = discard_channels(pp_recording, metadata, spykeparams['general']['discard_channels'])

    # SpikeSorting
    data = run_sorting(pp_recording, paths, metadata)

    # Curation
    if spykeparams['general']['do_curation']:
        data, units = run_curation(data, metadata, paths)

    if spykeparams['general']['export_to_phy']:
        phy_export(data, paths, units)

    print(f'\nEverything went well! You can access the folder {paths["working_folder"]} to check your results! Closing Spykeline...')

if __name__ == "__main__":
    gui = SpykelineGUI()
    gui_params, input_path, secondary_path, probe_list = gui.GUI()
    
    spykeparams = set_spykeparams(gui_params)

    run_spykeline(input_path, secondary_path, probe_list)