import os
import json
import time
import shutil

from . import set_spykeparams
from .GUI import SpykelineGUI
from .tools import define_paths, load_data, convert_json_compatible, open_sorting, export_results, delete_temp_files
from .preprocessing.preprocess import run_preprocessing
from .spikesorting.sorting import run_sorting
from .curation.curate import run_curation

def run_spykeline(input_path, secondary_path, spykeparams, probe_dict):
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
    start_time = time.time()

    print("Running Spykeline...")

    paths = define_paths(input_path, probe_dict, secondary_path)

    recording, metadata = load_data(paths, probe_dict)

    # Preprocessing
    pp_recording = run_preprocessing(recording,
                                      paths, 
                                      metadata)

    # SpikeSorting
    if spykeparams['general']['do_spikesort']:
        print("Starting SpikeSorting...")
        data = run_sorting(
            pp_recording, 
            paths, 
            metadata
            )
    else:
        print("Skipping SpikeSorting...")
        data = open_sorting(paths, pp_recording, metadata)

    # Curation
    if spykeparams['general']['do_curation']:
        if spykeparams['general']['pipeline'] == 'all':
            curated_data, units = run_curation(probe_data, metadata, paths)
        else:
            curated_data = []
            units = []
            for probe_id, probe_data in enumerate(data):
                curated_probe_data, probe_units = run_curation(probe_data, metadata, paths[f'Probe_{probe_id}'])
                curated_data.append(curated_probe_data)
                units.append(probe_units)

        print("Curation went well !!")
    else:
        curated_data = data
        units = None

    end_time = time.time()
    metadata['duration'] = end_time - start_time

    # Saving the metadata
    with open(os.path.join(paths['output_folder'], 'metadata.json'), 'w') as f:
        json.dump(metadata, f, default=convert_json_compatible)
    with open(os.path.join(paths['output_folder'], 'spykeparams.json'), 'w') as f:
        json.dump(spykeparams, f, default=convert_json_compatible)

    # Exporting the results
    export_results(curated_data,
                   paths,
                   units,
                   metadata)

    delete_temp_files(paths, metadata)

    print(f'\nTo check your results, access the folder: \n\n\t{paths["output_folder"]} \n\nClosing Spykeline...')

def main():

    gui = SpykelineGUI()
    gui_params, input_path, secondary_path, probe_dict = gui.GUI()

    for probe_id, probe in probe_dict.items():
        print(f"Probe {probe_id} : {probe['Brand']} {probe['Model']}")
    
    spykeparams = set_spykeparams(gui_params)

    run_spykeline(input_path, secondary_path, spykeparams, probe_dict)

if __name__ == "__main__":
    main()