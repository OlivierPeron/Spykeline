"""
Machine based variable configuration.

"""
import os
import sys

import spikeinterface.core as si

default_parameters = {
    "general": {
        "secondary_path": False,
        "discard_channels": [],
        "save_dat": False,
        "plot_probe": False,
        "do_spikesort": True,
        "do_curation": False,
        "export_to_phy": False,
        "export_to_klusters": False
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
        "folder": None, 
        "execution_mode": "Local",
        "sorter": "kilosort4",
        "pipeline": "by_probe",  # or 'all', default is 'by_probe'
    },
    "curation": {
        "recursive": True,
        "remove_noise_units": False, 
        "amplitude_threshold": 5000,
        "bin_size": 0.02,
        "distribution_threshold": 0.001,
        "correlation_threshold": 0.8
    }
}

parameters_description = {
    "general": {
        "secondary_path": "If True, the data will be output in this path, otherwise in the same folder as the raw data.",
        "discard_channels": "List of channels that you want to remove from the process (example: removing dead channels). Write the channels id separeted by a ',' such as: 17, 36, ...",
        "plot_probe": "Plot the probe layout. Default is False.",
        "export_to_phy": "Export the sorted spikes to phy format. Default is True.",
        "export_to_klusters": "Export the sorted spikes to klusters format. Default is False.",
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
        "amplitude_threshold": "Threshold on spike amplitude. Default is 5000.",
        "bin_size": "Bin size to create the distribution. Default is 0.02.",
        "distribution_threshold": "Proportion of spike used as a threshold to classify distributions. Default is 0.001.",
        "recursive": "Recursive curation. Default is True.",
        "remove_noise_units": "Either to delete units identify as noise. Default is False."
    }
}

home_probes = {
    'Buzsaki32': {
        'map': [16, 17, 18, 20, 21, 22, 31, 30, 29, 27, 26, 25, 24, 28, 23, 19, 12, 8, 3, 7, 6, 5, 4, 2, 1, 0, 9, 10, 11, 13, 14, 15],
        'shanks': [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3]
    },
    'Buzsaki64L': {
        'map': [49, 48, 51, 50, 53, 52, 55, 54, 57, 56, 59, 58, 61, 60, 63, 62, 32, 33, 34, 36, 37, 38, 40, 41, 42, 44, 45, 46, 47, 43, 39, 35, 29, 25, 21, 17, 16, 19, 18, 20, 23, 22, 24, 27, 26, 28, 31, 30, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
        'shanks': [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 6, 6, 6, 6, 6, 6, 6, 6, 7, 7, 7, 7, 7, 7, 7, 7]    
    }, 
    'Tetrode': {
        'map': [0, 1, 2, 3],
        'shanks': [0, 0, 0, 0]    
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
    print("Cupy not found. Using CPU. Install Cupy before launching Spykeline if you want to run it on GPU.")
    has_gpu = False

print(f'Using GPU: {has_gpu}')

if has_gpu:
    op = cp
else:
    import numpy as np
    op = np

### SETTING JOBS KWARGS DEPENDING ON CPU ###

si.set_global_job_kwargs(n_jobs=0.75,
                         chunk_size=20000,
                         progress_bar=True,
                         mp_context='spawn')

# Define the path to the cloned repository
repo_path = os.path.expanduser("~/probeinterface_library")

# Add the repository to the Python path
if os.path.exists(repo_path):
    if repo_path not in sys.path:
        sys.path.append(repo_path)
else:
    print(f"Error: Repository path {repo_path} does not exist.")

