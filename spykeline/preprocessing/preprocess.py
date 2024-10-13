import os
from pathlib import Path

import spikeinterface as si
import spikeinterface.preprocessing as spre
from probeinterface.plotting import plot_probe_group

from .. import spykeparams
from ..config import op, job_kwargs

from .probe import create_probe

def apply_filter(recording):
    """
    Get the filtering parameters from the parameters and launch the appropriate filter:
        - bandpass filter
        - lowpass filter
        - highpass filter
    """
    filter_params = spykeparams['preprocessing']['filter']
    if filter_params['freq_max'] is None:
        btype = "highpass"
        band = filter_params['freq_min']
    else:
        btype = "bandpass"
        band = [filter_params['freq_min'], filter_params['freq_max']]

    recording_filtered = spre.filter(recording=recording,
                                     band=band,
                                     btype=btype,
                                     ftype=filter_params['type'])

    return recording_filtered


def apply_common_ref(recording, metadata):
    """
    Apply a common reference to a recording. This common reference can be a channel, an average, or a median of the channels.

    Parameters
    ----------
    recording : recording
        A spikeinterface object. The recording to be spikesorted.
    metadata : dict
        Dict with channel map information.

    Returns
    -------
    recording_cr : recording
        Recording to which the common reference has been applied.
    """
    channel_groups = [[eval(j) for j in grp] for grp in metadata['Shanks_groups']]

    recording_cr = spre.common_reference(recording,
                                         reference='global',
                                         method=spykeparams['preprocessing']['common_reference']['method'],
                                         groups=channel_groups)
    
    return recording_cr


def run_preprocessing(recording, paths, metadata):
    """
    Preprocess the recording based on the defined Spykeline parameters.

    Parameters
    ----------
    recording : recording
        A spikeinterface object. The recording to be spikesorted.
    paths : dict
        Dictionary containing paths for saving/loading data.
    metadata : dict
        Dict with channel map information.

    Returns
    -------
    recording_loaded : recording
        Fully preprocessed recording.
    """
    pp_folder = os.path.join(paths['working_folder'], 'Preprocessed')

    if Path(pp_folder).is_dir():
        recording_loaded = si.load_extractor(pp_folder)
    else:
        recording_filtered = apply_filter(recording)
        recording_cmr = apply_common_ref(recording_filtered, metadata)
        
        # Create the recording's probes
        probegroup = create_probe(metadata)

        probegroup.set_global_device_channel_indices([channel for grp in metadata['Shanks_groups'] for channel in grp])

        # Check that the channel_ids are correct
        channel_ids = recording_cmr.get_channel_ids()
        channel_model = op.arange(0, metadata['nb_channels'], 1) 
        assert all(channel_ids[c] == channel_model[c] for c in channel_model), "Something is wrong with the way your channels are defined ..."

        recording_final = recording_cmr.set_probegroup(probegroup)

        if spykeparams['general']['plot_probe']:
            plot_probe_group(recording_final.get_probegroup(), with_device_index=True)

        if spykeparams['general']['save_dat']:
            os.makedirs(pp_folder, exist_ok=True)
            si.write_binary_recording(recording = recording_final, 
                                      file_paths = os.path.join(pp_folder, 'preprocessed_rec.dat'),
                                      dtype = 'uin16',
                                      **job_kwargs)

    return recording_final