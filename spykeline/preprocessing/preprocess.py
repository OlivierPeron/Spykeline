import os

import spikeinterface as si
import spikeinterface.preprocessing as spre

from collections import Counter, defaultdict

from .probe import create_probe
from ..tools import rename_annot

def apply_filter(recording):
    """
    Get the filtering parameters from the parameters and launch the appropriate filter:
        - bandpass filter
        - lowpass filter
        - highpass filter
    """
    from .. import spykeparams

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

def apply_common_ref(recording, channel_groups = None):
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
    from .. import spykeparams

    if channel_groups is None: # Applying CMR per radius
        recording_cr = spre.common_reference(recording,
                                             reference='local',
                                             operator=spykeparams['preprocessing']['common_reference']['method'],
                                             local_radius= (22, 55))
    else: # Default, applying CMR per shank
        recording_cr = spre.common_reference(recording,
                                             reference='global',
                                             operator=spykeparams['preprocessing']['common_reference']['method'],
                                             groups=channel_groups)
        
    return recording_cr

def run_preprocessing(recording, paths, metadata):
    """
    Preprocess the recording :
        - Apply a filter
        - Split the recording by probe
        - Discard the disconnected channels
        - Apply a common median reference (by shank or by radius if linear)
        - Whiten the probe recording

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
    recordings : list
        List of fully preprocessed recordings.
    """
    print("Preprocessing the recording...")
    from .. import spykeparams

    # Discard channels
    if Counter(spykeparams["general"]["discard_channels"]) == Counter(metadata["Disconected"]):
        all_ch_disc = metadata["Disconected"]
    else:
        all_ch_disc = spykeparams["general"]["discard_channels"]
    
    # Apply the initial filter
    recording_filtered = apply_filter(recording)

    probegroup, shanks_groups, metadata = create_probe(metadata)

    grouped = defaultdict(list)
    for row_keys, row_vals in zip(shanks_groups, metadata["Anatomical_groups"]):
        for k, v in zip(row_keys, row_vals):
            grouped[k].append(v)

    metadata["Shanks_groups"] = [grouped[k] for k in grouped.keys()]

    rec_probe = recording_filtered.set_probegroup(probegroup)

    if spykeparams['spikesorting']['pipeline'] == 'all':
        ch_keep = [ch for ch in rec_probe.get_channel_ids() if not ch in all_ch_disc]
        ch_disc = [ch for ch in rec_probe.get_channel_ids() if ch in all_ch_disc]
        if all(ch in ch_disc for ch in rec_probe.get_channel_ids()):
            raise ValueError("All the recording's channels are dicarded.")

        rec = rec_probe.select_channels(ch_keep)

        rec_cmr = apply_common_ref(rec, metadata["Shanks_groups"])

        # Apply whitening
        if spykeparams["preprocessing"]["whiten"]:
            rec_preprocessed = spre.whiten(rec_cmr, int_scale=1000)
        else:
            rec_preprocessed = rec_cmr

        rec_preprocessed.set_property("shank", [channel for probe in shanks_groups for channel in probe])

        if spykeparams["general"]["save_dat"]:
            pp_folder = paths['preprocessing']
            os.makedirs(pp_folder, exist_ok=True)
            si.write_binary_recording(
                recording=rec_preprocessed,
                file_paths=os.path.join(pp_folder, "preprocessed_rec.dat"),
                dtype="uint16",
                verbose=True
            )

        print("Preprocessing done!")

        return [rec_preprocessed]
    else:
        recordings = rec_probe.split_by('group', 'list')

        preprocessed_recordings = []

        for id, rec in enumerate(recordings):
            ch_keep = [ch for ch in rec.get_channel_ids() if not ch in all_ch_disc]
            ch_disc = [ch for ch in rec.get_channel_ids() if ch in all_ch_disc]
            if all(ch in ch_disc for ch in rec.get_channel_ids()):
                print(f"skipping probe {id}, as all its channels are to be discarded")
                continue
            
            rec = rec.select_channels(ch_keep)
            
            # Apply Common Reference
            if metadata['Probes'][id]['Architecture'] == 'Linear':
                rec_cmr = apply_common_ref(rec)
            else:
                shanks = [shank for shank in metadata["Shanks_groups"] if any(electrode in rec.get_channel_ids() for electrode in shank)]
                rec_cmr = apply_common_ref(rec, shanks)

            # Apply whitening
            if spykeparams["preprocessing"]["whiten"]:
                rec_preprocessed = spre.whiten(rec_cmr, int_scale=1000)
            else:
                rec_preprocessed = rec_cmr

            rec_preprocessed.set_property("shank", shanks_groups[id])

            rec_renamed = rename_annot(rec_preprocessed)

            preprocessed_recordings.append(rec_renamed)

        # Save the processed recording
        if spykeparams["general"]["save_dat"]:
            pp_folder = paths[f'Probe_{id}']['preprocessing']
            os.makedirs(pp_folder, exist_ok=True)
            si.write_binary_recording(
                recording=rec_renamed,
                file_paths=os.path.join(pp_folder, "preprocessed_rec.dat"),
                dtype="uint16",
                verbose=True
            )

        print("Preprocessing done!")

        return preprocessed_recordings