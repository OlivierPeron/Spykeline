"""
Machine based variable configuration.

"""
import os
import sys

home_probes = ['Buzsaki32', 'Buzsaki64L', 'Tetrode']

default_parameters = {
    "general": {
        "secondary_path": False,
        "discard_channels": [],
        "save_dat": False,
        "plot_probe": False,
        "export_to_phy": True,
        "amplifier_renamed": True,
        "do_curation": False
    },
    "preprocessing": {
        "filter": {
            "freq_min": 300,
            "freq_max": 9000,
            "type": "butter"
        },
        "common_reference": {
            "method": "median"
        }
    },
    "spikesorting": {
        "sorter": "kilosort2_5"
    },
    "curation": {
        "noise_amp_th": 5000,
        "distrib_th": 0.001,
        "recursive": True
    }
}

parameters_description = {
    "general": {
        "secondary_path": "If True, the data will be output in this path, otherwise in the same folder as the raw data.",
        "discard_channels": "List of channels that you want to remove from the process (example: removing dead channels). Write the channels id separeted by a ',' such as: 17, 36, ...",
        "plot_probe": "Plot the probe layout. Default is False.",
        "export_to_phy": "Export the sorted spikes to phy format. Default is True.",
        "amplifier_renamed": "If the amplifier.dat has not been renamed, set to True. Default is True.",
        "do_curation": "To include the curation step after spikesorting. Recommended, Spykeline has been developed for this step. Default is True."
    },
    "preprocessing": {
        "filter": {
            "freq_min": "Minimum frequency for the filter. Default is 300.",
            "freq_max": "Maximum frequency for the filter. Default is 9000.",
            "type": "Type of filter to use. Default is butter."
        },
        "common_reference": {
            "method": "Method to use for the common reference. Default is median."
        }
    },
    "spikesorting": {
        "sorter": "Sorter to use for the spikesorting. Default is kilosort2_5."
    },
    "curation": {
        "noise_amp_th": "Threshold for the noise amplitude. Default is 5000.",
        "distib_th": "Threshold for the distribution. Default is 0.001.",
        "recursive": "Recursive curation. Default is True."
    }
}

### SETTING LIBRARY DEPENDING ON GPU ###

try:
    import cupy as cp
    # Try to allocate a small array to check if GPU is really available
    try:
        _ = cp.array([1.0])
        has_gpu = True
    except Exception:
        has_gpu = False
except ImportError:
    has_gpu = False

if has_gpu:
    op = cp
else:
    import numpy as np
    op = np

### SETTING JOBS KWARGS DEPENDING ON CPU ###

max_jobs = os.cpu_count()
jobs = int(0.75 * max_jobs)

job_kwargs = dict(n_jobs=jobs,
                  chunk_duration="1s",
                  progress_bar=False)


# Define the path to the cloned repository
repo_path = os.path.expanduser("~/probeinterface_library")

# Add the repository to the Python path
if repo_path not in sys.path:
    sys.path.append(repo_path)

