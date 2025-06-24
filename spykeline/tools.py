import os
import json

import numpy as np

import spikeinterface.core as si
import spikeinterface.exporters as sexp 

from packaging.version import Version as V

from spykeline.config import op
from .spikesorting.sorter_params import sorter_dict

extensions_dict = {
    'waveforms' : {
        'ms_before': 1.5,
        'ms_after': 2.,
    },
    'random_spikes' : {
        'method': 'uniform',
        'max_spikes_per_unit': op.inf
    },
    'templates' : {
        'ms_before': 1.5,
        'ms_after': 2.0,
        'operators': ['median']
    },
    'spike_amplitudes': {
        'peak_sign': 'neg', 
    },
    'noise_levels': {
        'num_chunks_per_segment': 20,
        'chunk_size': 10000,
    },
    'principal_components': {
        'n_components': 5,
        'mode': 'by_channel_local',
        'whiten': True
    },
    'quality_metrics': {
        'metric_names': ['rp_violation', 
                         'num_spikes', 
                         'presence_ratio', 
                         'firing_rate', 
                         'amplitude_cutoff', 
                         'isi_violation', 
                         'snr', 
                         'amplitude_median', 
                         'amplitude_cv'],
        'qm_params': None,
        'peak_sign': None,
        'seed': None,
        'skip_pc_metrics': False
    }
}

def define_paths(base_folder, probe_dict, secondary_path = None):
    """
    Create a dictionary of required paths for Spykeline

    Parameters
    ----------
    base_folder : str or path
        Path to the folder containing input data.
    secondary_path : str or path
        Path to the secondary folder for output data.

    Returns
    -------
    paths : dict
        Dictionary containing all required paths
    """
    from spykeline import spykeparams

    session = os.path.basename(base_folder)

    print(f"Session: {session}")

    paths = {
        'base_folder' : base_folder,
        'dat' : os.path.join(base_folder, 'amplifier.dat'),
        'rhd' : os.path.join(base_folder, 'info.rhd')
    }

    dir_files = os.listdir(base_folder)
    if 'amplifier.dat' in dir_files:
        paths['dat'] = os.path.join(base_folder, 'amplifier.dat')
    elif f'{session}.dat' in dir_files:
        paths['dat'] = os.path.join(base_folder, session + '.dat')
    else:
        raise FileNotFoundError(f"Could not find the .dat file in {base_folder}. Please check the path or rename the file to either 'amplifier.dat' or {session}.dat.")

    if spykeparams['general']['secondary_path']:
        paths['output_folder'] = secondary_path
        if os.path.exists(os.path.join(paths['output_folder'], 'SpikeSorting')):
            # If the folder already exists, we create a new one with a different name
            i = 1
            while os.path.exists(os.path.join(paths['output_folder'], f'SpikeSorting_{i}')):
                i += 1
            paths['output_folder'] = os.path.join(paths['output_folder'], f'SpikeSorting_{i}')
        else:
            paths['output_folder'] = os.path.join(paths['output_folder'], 'SpikeSorting')
    else:
        if os.path.exists(os.path.join(base_folder, 'SpikeSorting')):
            # If the folder already exists, we create a new one with a different name
            i = 1
            while os.path.exists(os.path.join(base_folder, f'SpikeSorting_{i}')):
                i += 1
            paths['output_folder'] = os.path.join(base_folder, f'SpikeSorting_{i}')
        else:
            paths['output_folder'] = os.path.join(paths['base_folder'], 'SpikeSorting')
    
    if spykeparams['spikesorting']['pipeline'] == 'all':
        paths['tmp'] = os.path.join(paths['output_folder'], 'Tmp')
        paths['metadata'] = os.path.join(paths['output_folder'], 'Metadata')
        paths['preprocessing'] = os.path.join(paths['output_folder'], 'Preprocessing')

        if spykeparams['general']['do_curation']:
            paths['units'] = os.path.join(paths['metadata'], 'Original_units.pkl')
            paths['units_final'] = os.path.join(paths['metadata'], 'Final_units.pkl')

        if spykeparams['general']['export_to_phy']:
            paths['phy'] = os.path.join(paths['output_folder'], 'Phy')

        if spykeparams['general']['export_to_klusters']:
            paths['klusters'] = os.path.join(paths['output_folder'], 'Klusters')
    elif spykeparams['spikesorting']['pipeline'] == 'by_probe':
        if spykeparams['general']['mode'] == 'single':
            paths['Probe_0'] = {
                    'base_folder' : paths['output_folder'],
                    'metadata' : os.path.join(paths['output_folder'], 'Metadata'),
                    'tmp' : os.path.join(paths['output_folder'], 'Tmp'),
                    'preprocessing': os.path.join(paths['output_folder'], 'Preprocessing')
                }
            
            if spykeparams['general']['do_curation']:
                paths['Probe_0']['units'] = os.path.join(paths['Probe_0']['metadata'], 'Original_units.pkl')
                paths['Probe_0']['units_final'] = os.path.join(paths['Probe_0']['metadata'], 'Final_units.pkl')

            if spykeparams['general']['export_to_phy']:
                paths['Probe_0']['phy'] = os.path.join(paths['Probe_0']['base_folder'], 'Phy')

            if spykeparams['general']['export_to_klusters']:
                paths['Probe_0']['klusters'] = os.path.join(paths['Probe_0']['base_folder'], 'Klusters')
        else:
            for id, _ in enumerate(probe_dict):
                paths[f'Probe_{id}'] = {
                    'base_folder' : os.path.join(paths['output_folder'], f'Probe_{id}'),
                    'metadata' : os.path.join(paths['output_folder'], f'Probe_{id}', 'Metadata'),
                    'tmp' : os.path.join(paths['output_folder'], f'Probe_{id}', 'Tmp'),
                    'preprocessing': os.path.join(paths['output_folder'], f'Probe_{id}', 'Preprocessing')
                }

                if spykeparams['general']['do_curation']:
                    paths[f'Probe_{id}']['units'] = os.path.join(paths[f'Probe_{id}']['metadata'], 'Original_units.pkl')
                    paths[f'Probe_{id}']['units_final'] = os.path.join(paths[f'Probe_{id}']['metadata'], 'Final_units.pkl')

                if spykeparams['general']['export_to_phy']:
                    paths[f'Probe_{id}']['phy'] = os.path.join(paths[f'Probe_{id}']['base_folder'], 'Phy')

                if spykeparams['general']['export_to_klusters']:
                    paths[f'Probe_{id}']['klusters'] = os.path.join(paths[f'Probe_{id}']['base_folder'], 'Klusters')

    return paths

def read_rhd(filepath):
    """
    Read and parse a RHD file.

    Parameters
    ----------
    path : str
        Path to the .rhd file.

    Returns
    -------
    intan_info : IntanRecordingExtractor
        Information about the recording, that is from the Intan's .rhd file.
    """
    rhd_global_header_base = [
        ("magic_number", "uint32"),  # 0xC6912702
        ("major_version", "int16"),
        ("minor_version", "int16"),
    ]

    rhd_global_header_part1 = [
        ("sampling_rate", "float32"),
        ("dsp_enabled", "int16"),
        ("actual_dsp_cutoff_frequency", "float32"),
        ("actual_lower_bandwidth", "float32"),
        ("actual_upper_bandwidth", "float32"),
        ("desired_dsp_cutoff_frequency", "float32"),
        ("desired_lower_bandwidth", "float32"),
        ("desired_upper_bandwidth", "float32"),
        ("notch_filter_mode", "int16"),
        ("desired_impedance_test_frequency", "float32"),
        ("actual_impedance_test_frequency", "float32"),
        ("note1", "QString"),
        ("note2", "QString"),
        ("note3", "QString"),
    ]

    rhd_global_header_v11 = [
        ("num_temp_sensor_channels", "int16"),
    ]

    rhd_global_header_v13 = [
        ("eval_board_mode", "int16"),
    ]

    rhd_global_header_v20 = [
        ("reference_channel", "QString"),
    ]

    rhd_global_header_final = [
        ("nb_signal_group", "int16"),
    ]

    rhd_signal_group_header = [
        ("signal_group_name", "QString"),
        ("signal_group_prefix", "QString"),
        ("signal_group_enabled", "int16"),
        ("channel_num", "int16"),
        ("amplified_channel_num", "int16"),
    ]

    rhd_signal_channel_header = [
        ("native_channel_name", "QString"),
        ("custom_channel_name", "QString"),
        ("native_order", "int16"),
        ("custom_order", "int16"),
        ("signal_type", "int16"),
        ("channel_enabled", "int16"),
        ("chip_channel_num", "int16"),
        ("board_stream_num", "int16"),
        ("spike_scope_trigger_mode", "int16"),
        ("spike_scope_voltage_thresh", "int16"),
        ("spike_scope_digital_trigger_channel", "int16"),
        ("spike_scope_digital_edge_polarity", "int16"),
        ("electrode_impedance_magnitude", "float32"),
        ("electrode_impedance_phase", "float32"),
    ]

    def read_qstring(f):
        length = np.fromfile(f, dtype="uint32", count=1)[0]
        if length == 0xFFFFFFFF or length == 0:
            return ""
        txt = f.read(length).decode("utf-16")
        return txt

    def read_variable_header(f, header):
        info = {}
        for field_name, field_type in header:
            if field_type == "QString":
                field_value = read_qstring(f)
            else:
                field_value = np.fromfile(f, dtype=field_type, count=1)[0]
            info[field_name] = field_value
        return info

    with open(filepath, mode="rb") as f:

        global_info = read_variable_header(f, rhd_global_header_base)

        version = V("{major_version}.{minor_version}".format(**global_info))

        # the header size depends on the version :-(
        header = list(rhd_global_header_part1)  # make a copy

        if version >= V("1.1"):
            header = header + rhd_global_header_v11
        else:
            global_info["num_temp_sensor_channels"] = 0

        if version >= V("1.3"):
            header = header + rhd_global_header_v13
        else:
            global_info["eval_board_mode"] = 0

        if version >= V("2.0"):
            header = header + rhd_global_header_v20
        else:
            global_info["reference_channel"] = ""

        header = header + rhd_global_header_final

        global_info.update(read_variable_header(f, header))

        # read channel group and channel header
        channels_by_type = {k: [] for k in [0, 1, 2, 3, 4, 5]}
        for g in range(global_info["nb_signal_group"]):
            group_info = read_variable_header(f, rhd_signal_group_header)

            if bool(group_info["signal_group_enabled"]):
                for c in range(group_info["channel_num"]):
                    chan_info = read_variable_header(f, rhd_signal_channel_header)
                    if bool(chan_info["channel_enabled"]):
                        channels_by_type[chan_info["signal_type"]].append(chan_info)

    sr = global_info["sampling_rate"]

    # construct the data block dtype and reorder channels
    if version >= V("2.0"):
        BLOCK_SIZE = 128
    else:
        BLOCK_SIZE = 60  # 256 channels

    ordered_channels = []

    if version >= V("1.2"):
        data_dtype = [("timestamp", "int32", BLOCK_SIZE)]
    else:
        data_dtype = [("timestamp", "uint32", BLOCK_SIZE)]

    # 0: RHD2000 amplifier channel
    for chan_info in channels_by_type[0]:
        name = chan_info["native_channel_name"]
        chan_info["sampling_rate"] = sr
        chan_info["units"] = "uV"
        chan_info["gain"] = 0.195
        chan_info["offset"] = -32768 * 0.195
        ordered_channels.append(chan_info)
        data_dtype += [(name, "uint16", BLOCK_SIZE)]

    # 1: RHD2000 auxiliary input channel
    for chan_info in channels_by_type[1]:
        name = chan_info["native_channel_name"]
        chan_info["sampling_rate"] = sr / 4.0
        chan_info["units"] = "V"
        chan_info["gain"] = 0.0000374
        chan_info["offset"] = 0.0
        ordered_channels.append(chan_info)
        data_dtype += [(name, "uint16", BLOCK_SIZE // 4)]

    # 2: RHD2000 supply voltage channel
    for chan_info in channels_by_type[2]:
        name = chan_info["native_channel_name"]
        chan_info["sampling_rate"] = sr / BLOCK_SIZE
        chan_info["units"] = "V"
        chan_info["gain"] = 0.0000748
        chan_info["offset"] = 0.0
        ordered_channels.append(chan_info)
        data_dtype += [(name, "uint16")]

    # temperature is not an official channel in the header
    for i in range(global_info["num_temp_sensor_channels"]):
        name = "temperature_{}".format(i)
        chan_info = {"native_channel_name": name, "signal_type": 20}
        chan_info["sampling_rate"] = sr / BLOCK_SIZE
        chan_info["units"] = "Celsius"
        chan_info["gain"] = 0.001
        chan_info["offset"] = 0.0
        ordered_channels.append(chan_info)
        data_dtype += [(name, "int16")]

    # 3: USB board ADC input channel
    for chan_info in channels_by_type[3]:
        name = chan_info["native_channel_name"]
        chan_info["sampling_rate"] = sr
        chan_info["units"] = "V"
        if global_info["eval_board_mode"] == 0:
            chan_info["gain"] = 0.000050354
            chan_info["offset"] = 0.0
        elif global_info["eval_board_mode"] == 1:
            chan_info["gain"] = 0.00015259
            chan_info["offset"] = -32768 * 0.00015259
        elif global_info["eval_board_mode"] == 13:
            chan_info["gain"] = 0.0003125
            chan_info["offset"] = -32768 * 0.0003125
        ordered_channels.append(chan_info)
        data_dtype += [(name, "uint16", BLOCK_SIZE)]

    # 4: USB board digital input channel
    # 5: USB board digital output channel
    for sig_type in [4, 5]:
        # Now these are included so that user can obtain the
        # dig signals and process them at the same time
        if len(channels_by_type[sig_type]) > 0:
            name = {4: "DIGITAL-IN", 5: "DIGITAL-OUT"}[sig_type]
            chan_info = channels_by_type[sig_type][0]
            chan_info["native_channel_name"] = name  # overwite to allow memmap to work
            chan_info["sampling_rate"] = sr
            chan_info["units"] = "TTL"  # arbitrary units so I did TTL for the logic
            chan_info["gain"] = 1.0
            chan_info["offset"] = 0.0
            ordered_channels.append(chan_info)
            data_dtype += [(name, "uint16", BLOCK_SIZE)]

    if bool(global_info["notch_filter_mode"]) and version >= V("3.0"):
        global_info["notch_filter_applied"] = True
    else:
        global_info["notch_filter_applied"] = False

    # Post_processing
    intan_info = {}
    intan_info['sampling_rate'] = global_info['sampling_rate']
    intan_info['Probe_channels'] = []

    ## Channels
    acc_ch = []
    curr_probe = None
    ch_offset = 0
    for chan_info in ordered_channels:
        if chan_info["signal_type"] == 0: # Amplifier channels
            probe_name = chan_info["native_channel_name"].split("-")[0]
            if curr_probe == None:
                probe_ch = []
                curr_probe = probe_name
                intan_info['gain_to_uV'] = chan_info["gain"]
                intan_info['offset_to_uV'] = chan_info["offset"]
            elif probe_name != curr_probe:
                probe_channels = [channel + ch_offset for channel in probe_ch]
                ch_offset += len(probe_ch)
                intan_info['Probe_channels'].append(probe_channels)
                probe_ch = []
                curr_probe = probe_name
            probe_ch.append(chan_info["native_order"])
        elif chan_info["signal_type"] == 1: # Auxiliary channels
            if curr_probe != None:
                probe_channels = [channel + ch_offset for channel in probe_ch]
                ch_offset += len(probe_ch)
                intan_info['Probe_channels'].append(probe_channels)
                curr_probe = None
            acc_ch.append(chan_info["native_order"])
        else:
            pass
    intan_info['accelerometer_channels'] = np.arange(len(acc_ch)) + ch_offset

    intan_info['num_channels'] = len(acc_ch) + ch_offset

    return intan_info

def load_data(paths, probe_dict):
    """
    Load the data from the paths.

    Parameters
    ----------
    paths : dict
        Contains all required paths.

    Returns
    -------
    recording : spikeinterface.core.BaseRecording
        The recording in spikeinterface format.
    metadata : dict
        Dict with channel map information.
    """
    from . import spykeparams

    ## METADATA
    if os.path.exists(os.path.join(paths['base_folder'], 'metadata.json')): # Case of a second run, or non-intan recording (i.g. GG's data)
        with open(os.path.join(paths['base_folder'], 'metadata.json'), 'rb') as f:
            metadata = json.load(f)
        metadata['Probes'] = probe_dict
        metadata['Nb_channels'] = int(metadata['Nb_channels'])
        metadata['Sampling_rate'] = int(metadata['Sampling_rate'])
        metadata['Session'] = os.path.basename(paths['base_folder'])
        metadata['Accelerometer'] = metadata['Anatomical_groups'][-1]
        metadata['Anatomical_groups'] = metadata['Anatomical_groups'][:-1]
        metadata['Shanks_groups'] = metadata['Shanks_groups'][:-1]

        if not "Disconected" in metadata.keys():
            metadata['Disconected'] = spykeparams['general']['discard_channels']

    else: # Generic case
        intan_info = read_rhd(paths['rhd'])

        metadata = {
            "Anatomical_groups": intan_info['Probe_channels'],
            "Accelerometer": intan_info['accelerometer_channels'],
            "Nb_channels": intan_info['num_channels'],
            "Disconected": spykeparams['general']['discard_channels'],
            "Probes": probe_dict,
            "Session": os.path.basename(paths['base_folder']),
            "Gain_to_uV": intan_info['gain_to_uV'],
            "Offset_to_uV": intan_info['offset_to_uV'],
            "Sampling_rate": intan_info['sampling_rate'],
            "Dtype": 'int16',
            "Filtered": False
        }

    for channel in metadata['Disconected']:
        if channel in metadata['Accelerometer']:
            metadata['Disconected'].remove(channel)

    ## RECORDING
    # → channel Gain and Offset (from Intan documentation)
    rec_gains = metadata['Gain_to_uV']
    rec_offsets = metadata['Offset_to_uV']
    
    # Opening of the recording
    raw_recording = si.read_binary(paths['dat'],
                                   metadata['Sampling_rate'],
                                   metadata['Dtype'], 
                                   metadata['Nb_channels'],                 
                                   gain_to_uV=rec_gains,
                                   offset_to_uV=rec_offsets,
                                   is_filtered=metadata['Filtered']) 
    
    # Removing accelerometer channels
    recording = raw_recording.remove_channels(metadata['Accelerometer'])

    return recording, metadata

def open_sorting(paths, recordings, metadata):
    """
    Open the sorting from the paths.

    Parameters
    ----------
    paths : dict
        Contains all required paths.
    recording : list
        List of spikeinterface.core.BaseRecording, default spikeinterface recording format.
    metadata : dict
        Dict with channel map information.

    Returns
    -------
    sorting : spikeinterface.sorting.BaseSorting
        The sorting in spikeinterface format.
    """
    from . import spykeparams

    entries  = os.listdir(spykeparams['spikesorting']['folder'])

    nb_folders = sum(1 for entry in entries if os.path.isdir(os.path.join(spykeparams['spikesorting']['folder'], entry)))

    if nb_folders == len(recordings):
        folder_mode = 'multiple'
    else:
        folder_mode = 'single'

    if folder_mode == 'single':
        sorting = sorter_dict[spykeparams['spikesorting']['sorter']]['extractor'](spykeparams['spikesorting']['folder'])
        units_ids = sorting.unit_ids
    
        data = []
        for probe_id, probe_channels in enumerate(metadata['Anatomical_groups']):
            assert 'ch' in sorting.get_property_keys()
            units_ch = sorting.get_property('ch')
            mask = np.isin(units_ch, probe_channels)
            probe_sorting = sorting.select_units(units_ids[mask])

            final_recording, final_sorting, sorting_analyzer = exporter(id, 
                                                                        rec,
                                                                        probe_sorting,
                                                                        paths[f'Probe_{id}'],
                                                                        metadata)
            final_sorting.register_recording(final_recording)

            data.append({
                'sorting': final_sorting,
                'sorting_analyzer': sorting_analyzer
                })

    else:
        folders = [entry for entry in entries if os.path.isdir(os.path.join(spykeparams['spikesorting']['folder'], entry))]

        data = []
        for probe_id, rec in enumerate(recordings):
            folder_name = [folder for folder in folders if probe_id in folder]
            current_folder = os.path.join(spykeparams['spikesorting']['folder'], folder_name[0])
            try:
                if 'path' in sorter_dict[spykeparams['spikesorting']['sorter']].keys():
                    current_folder = os.path.join(current_folder, sorter_dict[spykeparams['spikesorting']['sorter']]['path'])
                sorting = sorter_dict[spykeparams['spikesorting']['sorter']]['extractor'](current_folder)
            except Exception as e:
                print("Didn't manage to open your sorting...")
                print(f"Unexpected error occurred: {e}")

            final_recording, final_sorting, sorting_analyzer = exporter(id, 
                                                                        rec,
                                                                        sorting,
                                                                        paths[f'Probe_{id}'],
                                                                        metadata)
            
            final_sorting.register_recording(final_recording)

            data.append({
                'sorting': final_sorting,
                'sorting_analyzer': sorting_analyzer
                })

    
    return data

def loader(sorting_analyzer, extension: str):
    """
    Load or compute any extension, taking kwargs from extensions_dict.

    Parameters
    ----------
    sorting_analyzer : 
        spikeinterface sorting analyzer object
    extension: str
        Name of the required extension

    Returns
    -------
    loaded_ext : list
        The required extension
    """  
    saved_ext = sorting_analyzer.get_saved_extension_names()

    if extension == 'waveforms' and not 'random_spikes' in saved_ext:
        loader(sorting_analyzer, 'random_spikes')
    elif extension == 'principal_components' and not 'waveforms' in saved_ext:
        loader(sorting_analyzer, 'waveforms')
    elif extension == 'quality_metrics' and not {'noise_levels', 'spike_amplitudes'}.issubset(saved_ext):
        loader(sorting_analyzer, 'noise_levels')
        loader(sorting_analyzer, 'spike_amplitudes')
    elif extension == 'templates' and not 'waveforms' in saved_ext:
        loader(sorting_analyzer, 'waveforms')
        
    kwargs = extensions_dict[extension]

    if extension in sorting_analyzer.get_loaded_extension_names():
        loaded_ext = sorting_analyzer.get_extension(extension)
    else:
        loaded_ext = sorting_analyzer.compute(extension, 
                                              **kwargs)
        
    return loaded_ext

def rename_annot(data):
    """
    Rename the "split_by property" annotation.
    """

    if 'split_by_property' in data._annotations.keys():
        value = data._annotations['split_by_property']
        new_key = f'split_by_{value}'
        data._annotations[new_key] = value
        del data._annotations['split_by_property']
    
    return data

def convert_json_compatible(obj):
    if isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.bool_)):
        return bool(obj)
    else:
        raise TypeError(f"Type {type(obj)} not serializable")

def exporter(id, recording, sorting, folder, metadata:dict, mode:int = 0):
    """
    Export the sorting into a sorting analyzer sparse, with required properties.

    Parameters
    ----------
    recording : recording
        A spikeinterface object. The recording to spikesort.
    sorting : sorting
        A spikeinterface sorting object.
    folder : dict
        Dict with all the required paths.
    metadata : dict
        Dict with channel map information.
    mode : int
        The mode of the export. 
            0 for the pre-curation export, 
            1 for the export if skip curation.

    Returns
    -------
    recording :
        A spikeinterface recording object.
    sorting :
        A spikeinterface sorting object.
    sorting_analyzer :
        A spikeinterface sorting_analyzer object.
    """
    if mode == 0:
        name = 'Analyzer'
    elif mode == 1:
        name = 'Final_analyzer'
    else:
        raise ValueError('Mode should be either 0 or 1')
    
    dense_path = os.path.join(folder['tmp'], f'{name}_dense')
    final_sa_path = os.path.join(folder['Metadata'], f'{name}_sparsed')

    # Need a Analyzer for computing the sparsity
    dense_analyzer = si.create_sorting_analyzer(sorting,
                                                recording,
                                                folder=dense_path,
                                                format='binary_folder',
                                                sparse=False)
    
    if id is None:
        shank_groups = [
            shank_id
            for shank_id, shank in enumerate(metadata["Shanks_groups"])
            for _ in shank
        ]
    else:
        shank_groups = [
            shank_id
            for shank_id, shank in enumerate(metadata["Shanks_groups"])
            if shank[0] in metadata["Anatomical_groups"][id]
            for _ in shank
        ]
    
    if not 'shank' in recording.get_property_keys():
        recording.set_property('shank', shank_groups)

    if not 'shank' in dense_analyzer.recording.get_property_keys():
        dense_analyzer.recording.set_property('shank', shank_groups)

    loader(dense_analyzer, 'waveforms')
    loader(dense_analyzer, 'templates')
    max_amp_ch = si.get_template_extremum_channel(dense_analyzer, 
                                                  peak_sign='both', 
                                                  mode='extremum')

    group_prop = [
        shank_id
        for _, max_ch in max_amp_ch.items()
        for shank_id, shank in enumerate(metadata["Shanks_groups"])
        if max_ch in shank
    ]

    sorting.set_property('shank', group_prop)
    dense_analyzer.sorting.set_property('shank', group_prop)

    sparsity = si.compute_sparsity(dense_analyzer,
                                   method='by_property',
                                   peak_sign='both',
                                   by_property='shank')
    
    # delete the dense analyzer
    # if os.path.isdir(dense_path):
    #     shutil.rmtree(dense_path)

    sorting_analyzer = si.create_sorting_analyzer(sorting,
                                                  recording,
                                                  folder=final_sa_path,
                                                  format='binary_folder',
                                                  sparsity=sparsity)
    if mode == 0:
        loader(sorting_analyzer, 'templates')
    
    return recording, sorting, sorting_analyzer

def phy_export(data, folder, units):
    """
    Export data to Phy format.

    Parameters
    ----------
    data : dict
        Contains :
            - 'sorting' : a spikeinterface sorting object
            - 'sorting_analyzer' : a spikeinterface sorting_analyzer object.
    paths : dict
        Contains all required paths
    units : dict
        Contains unit information, optional.

    Returns
    -------
    None.
    """
    # from . import spykeparams

    sorting_analyzer = data['sorting_analyzer']

    os.makedirs(folder['phy'], exist_ok=True)

    qms = loader(sorting_analyzer, 
                 "quality_metrics", 
                 metric_names=['firing_rate', 'amplitude_median'], 
                 skip_pc_metrics=True)

    metrics = qms.get_data()

    sorting_analyzer.set_sorting_property('fr',  [fr for fr in metrics["firing_rate"]], save = True)
    sorting_analyzer.set_sorting_property('Amp', [amp for amp in metrics["amplitude_median"]], save = True)

    if units is not None:
        sorting_analyzer.set_sorting_property('ch', [units[unit].main_ch for unit in sorting_analyzer.unit_ids], save = True)
        sorting_analyzer.set_sorting_property('shank', [units[unit].mother for unit in sorting_analyzer.unit_ids], save = True)
        sorting_analyzer.set_sorting_property('n_spikes', [units[unit].nb_spikes for unit in sorting_analyzer.unit_ids], save = True)

    sexp.export_to_phy(sorting_analyzer,
                       output_folder = folder['phy'],
                       compute_amplitudes = False,
                       compute_pc_features = True,
                       copy_binary = True,
                       remove_if_exists = True,
                       template_mode = "median")
    
    # if units is not None:
    #     for property in os.listdir(phy_folder):
    #         if property.endswith('.tsv'):
    #             file = os.path.join(phy_folder, property)
    #             os.remove(file)
        
    #     qms = loader(sorting_analyzer, 
    #                 "quality_metrics", 
    #                 metric_names=['firing_rate', 'amplitude_median'], 
    #                 skip_pc_metrics=True)

    #     metrics = qms.get_data()
        
    #     cluster_info = pd.DataFrame(
    #         {"id": [u_id for u_id in sorting_analyzer.unit_ids], 
    #         "ch": [units[unit].main_ch for unit in sorting_analyzer.unit_ids],
    #         "shank": [units[unit].mother for unit in sorting_analyzer.unit_ids], 
    #         "probe": [units[unit].probe for unit in sorting_analyzer.unit_ids], 
    #         "fr": [fr for fr in metrics["firing_rate"]],
    #         "Amp": [amp for amp in metrics["amplitude_median"]],
    #         "n_spikes": [units[unit].nb_spikes for unit in sorting_analyzer.unit_ids]
    #         }
    #     )
    #     cluster_info.to_csv(os.path.join(phy_folder, "cluster_info.tsv"), sep="\t", index=False)

    print(f"Your data has been exported to phy format!\nTo open it run the following line in the terminal:\n\n phy template-gui {os.path.join(folder['phy'], 'params.py')}")

def klusters_export(
        data: dict,
        folder: dict,
        metadata: dict
    ):
    """
    Export a SpikeInterface Sorting / SortingAnalyzer to Klusters format
    (.clu, .res, .fet, .spk). A minimal .xml describing the probe geometry
    is still required by Klusters but is not written here.

    Parameters
    ----------
    data : dict
        {
            'sorting'          : spikeinterface Sorting,
            'sorting_analyzer' : spikeinterface SortingAnalyzer
        }
    folder : dict
        {'klusters': <output directory>}
    metadata : dict
        Must contain:
            - 'Session'                : file prefix, e.g. 'Mouse42_2025-06-18'
            - 'channel_groups' (dict)  : {shank_id: [channel indices]}
    """
    required_props = ['sh', 'ch', 'original_cluster_id', 'n_spikes']
    sorting          = data['sorting']
    sorting_analyzer = data['sorting_analyzer']

    # ---------- sanity checks ----------
    for prop in required_props:
        if prop not in sorting.get_property_keys():
            raise ValueError(f"Missing required property: {prop}")

    # ---------- make sure we have waveforms and PCA features ----------
    # Waveforms
    loader(sorting_analyzer, 'waveforms')
    # Principal components
    loader(sorting_analyzer, 'principal_components')

    n_shanks = len(np.unique(sorting.get_property('sh')))

    for sh_id in range(n_shanks):
        chan_ids_in_shank = metadata['channel_groups'][sh_id]
        units_on_shank    = np.unique(
            sorting.get_property('original_cluster_id')
                    [sorting.get_property('sh') == sh_id])

        if len(units_on_shank) == 0:
            continue

        # --- gather spike-level information for this shank -------------
        all_spk_times   = []
        all_labels      = []
        all_feat_rows   = []
        all_wave_rows   = []

        for unit_id in units_on_shank:
            st           = sorting.get_unit_spike_train(unit_id)
            n_spikes     = len(st)

            # cluster labels BEFORE remap – we’ll remap later
            all_labels.append(np.full(n_spikes, unit_id, dtype=np.int32))
            all_spk_times.append(st)

            # PCA features: (n_spikes, n_components, n_channels_tot)
            pc = sorting_analyzer.get_features(unit_id, feature_name='principal_components')
            # keep only the channels belonging to this shank and flatten:
            pc = pc[:, :, chan_ids_in_shank].transpose(0, 2, 1).reshape(n_spikes, -1)
            all_feat_rows.append(pc)

            # Waveforms: (n_spikes, n_chan_tot, n_samp)
            wfs = sorting_analyzer.get_waveforms(unit_id)[:, chan_ids_in_shank, :]
            # flatten channel-major so Klusters reads correctly
            all_wave_rows.append(wfs.reshape(n_spikes, -1))

        dtype_waveforms = type(wfs)

        # ---------- concatenate & sort by time -------------------------
        spk_times = np.concatenate(all_spk_times)
        labels    = np.concatenate(all_labels)
        feats     = np.concatenate(all_feat_rows)
        waves     = np.concatenate(all_wave_rows)

        sort_idx  = np.argsort(spk_times)
        spk_times = spk_times[sort_idx]
        labels    = labels[sort_idx]
        feats     = feats[sort_idx]
        waves     = waves[sort_idx]

        # ---------- remap cluster IDs to 0…N-1 -------------------------
        uniques         = np.unique(labels)
        label_map       = {old: new for new, old in enumerate(uniques)}
        labels_remapped = np.vectorize(label_map.get)(labels)
        n_clusters      = len(uniques)

        # ---------- scale features to integer range for .fet -----------
        # Klusters expects integers; a simple linear scale [0, 2**16-1]
        feat_min = feats.min(axis=0)
        feat_max = feats.max(axis=0)
        denom    = (feat_max - feat_min)
        denom[denom == 0] = 1   # avoid /0 for flat features
        feats_scaled = np.round(
            (feats - feat_min) / denom * (2**16 - 1)
        ).astype(np.int32)

        # ---------- scale waveforms to chosen dtype --------------------
        wf_max = np.abs(waves).max()
        if wf_max == 0:
            wf_max = 1           # safety
        scale  = np.iinfo(dtype_waveforms).max / wf_max
        waves_scaled = np.round(waves * scale).astype(dtype_waveforms)

        # ---------- write the four Klusters files ----------------------
        prefix = os.path.join(folder['klusters'],
                              f"{metadata['Session']}.{sh_id:08d}")

        # .clu
        with open(prefix.replace(f".{sh_id:08d}", f".clu.{sh_id}"), 'w') as f:
            f.write(f"{n_clusters}\n")
            f.writelines(f"{lab}\n" for lab in labels_remapped)

        # .res
        with open(prefix.replace(f".{sh_id:08d}", f".res.{sh_id}"), 'w') as f:
            f.writelines(f"{t}\n" for t in spk_times)

        # .fet
        with open(prefix.replace(f".{sh_id:08d}", f".fet.{sh_id}"), 'w') as f:
            f.write(f"{feats_scaled.shape[1]}\n")  # first line = n_dims
            for row in feats_scaled:
                f.write(" ".join(map(str, row)) + "\n")

        # .spk  (raw binary, no header)
        waves_scaled.tofile(prefix.replace(f".{sh_id:08d}", f".spk.{sh_id}"))

    print("Finished writing .clu / .res / .fet / .spk files")

def export_results(data, paths, units, metadata):
    """
    Export the results to phy and klusters format.

    Parameters
    ----------
    data : dict
        Contains :
            - 'sorting' : a spikeinterface sorting object
            - 'sorting_analyzer' : a spikeinterface sorting_analyzer object.
    paths : dict
        Contains all required paths.
    units : dict
        Contains unit information, optional.
    """
    from . import spykeparams

    # Exporting to phy
    if spykeparams['general']['export_to_phy']:
        if spykeparams['general']['pipeline'] == 'all':
            phy_export(data,
                       paths,
                       units)
        else:
            for probe_id, _ in metadata['Probes'].items():
                phy_export(data[probe_id],
                        paths[f'Probe_{probe_id}'],
                        units[probe_id])
                
    # Exporting to klusters
    if spykeparams['general']['export_to_klusters']:
        if spykeparams['general']['pipeline'] == 'all':
            klusters_export(data,
                            paths,
                            units)
        else:
            for probe_id, _ in metadata['Probes'].items():
                klusters_export(data[probe_id],
                                paths[f'Probe_{probe_id}'],
                                units[probe_id])