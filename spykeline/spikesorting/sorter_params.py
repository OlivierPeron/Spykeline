import os
import spikeinterface.core as si
import spikeinterface.extractors as se 

sorter_dict = {
    'kilosort2_5' : {'surname' : "KS25",
                     'docker_image' : None,  # "spikeinterface/kilosort2_5-compiled-base:latest",
                     'params' : {
                                'detect_threshold': 6,
                                'projection_threshold': [10, 4],
                                'preclust_threshold': 8,
                                'car': False,
                                'minFR': 0.3,
                                'minfr_goodchannels': 0.2,
                                'nblocks': 5,
                                'sig': 20,
                                'freq_min': 300,
                                'sigmaMask': 30,
                                'nPCs': 3,
                                'ntbuff': 64,
                                'nfilt_factor': 4,
                                'NT': None,
                                'do_correction': True,
                                'wave_length': 61,
                                'keep_good_only': False,
                                'lam' : 15
                                },
                     'extractor' : se.KiloSortSortingExtractor,
                     'path' : 'sorter_output'
                     },
    
    'kilosort3' : {'surname' : "KS3",
                   'docker_image' : "spikeinterface/kilosort3-compiled-base:latest",
                   'params' : {
                               'detect_threshold': 6,
                               'projection_threshold': [10, 6],
                               'preclust_threshold': 8,
                               'car': False,
                               'minFR': 0.02,
                               'minfr_goodchannels': 0.1,
                               'nblocks': 5,
                               'sig': 20,
                               'freq_min': 300,
                               'sigmaMask': 30,
                               'nPCs': 3,
                               'ntbuff': 64,
                               'nfilt_factor': 4,
                               'do_correction': True,
                               'NT': None,
                               'wave_length': 61,
                               'keep_good_only': False
                               },
                   'extractor' : se.KiloSortSortingExtractor,
                    'path' : 'sorter_output'
                   },
    
    'kilosort4' : {'surname' : "KS4",
                   'docker_image' : "spikeinterface/kilosort3-compiled-base:latest",
                   'params' : {
                               'Th_universal': 9,
                               'Th_learned': 8,
                               'do_CAR': False,
                               'nearest_chans': 3,
                               'whitening_range': None,  # Nb of neighbor channels to use for whitening, default 32.
                               'nt0min': 30,
                               'n_pcs': 6,  # Here, pcs must be 4 for tetrodes and 8 for probes (if by shank, else 32 or 64 depending of the probe)
                               'do_correction' : False,  # Whether or not to perform drift correction
                               'skip_kilosort_preprocessing': True,  # opposite of do_CAR 
                               },
                   'extractor' : se.KiloSortSortingExtractor,
                    'path' : 'sorter_output'
                   },
    
    'mountainsort4' : {'surname' : "MS4",
                       'docker_image' : "spikeinterface/mountainsort4-base:latest",
                       'params' : {
                                   'detect_sign': -1,  # Use -1, 0, or 1, depending on the sign of the spikes in the recording
                                   'adjacency_radius': -1,  # Use -1 to include all channels in every neighborhood
                                   'freq_min': 300,  # Use None for no bandpass filtering
                                   'freq_max': 6000,
                                   'filter': False,
                                   'whiten': True,  # Whether to do channel whitening as part of preprocessing
                                   'num_workers': 1,
                                   'clip_size': 50,
                                   'detect_threshold': 3,
                                   'detect_interval': 10,  # Minimum number of timepoints between events detected on the same channel
                                   'tempdir': None
                                   },
                       'extractor' : si.read_npz_sorting  # se.MdaSortingExtractor
                       },
    
    'mountainsort5' : {'surname' : "MS5",
                       'docker_image' : "spikeinterface/mountainsort5-base:latest",
                       'params' : {
                            'scheme': '3',  # '1', '2', '3' 3 Might be better as we have a long recording
                            'detect_threshold': 5.5,  # this is the recommended detection threshold
                            'detect_sign': -1,
                            'detect_time_radius_msec': 0.5,  # This should be the time of the absolute refractory period -> To check
                            'detect_channel_radius': None,  # the length around the channel with highest waveform amp to apply detect_time_radius_msec (None = applied infinitely so all channel are blocked -> bad; except if sorted by group)
                            'snippet_T1': 20,  # before the spike 
                            'snippet_T2': 20,  # after
                            'snippet_mask_radius': None,
                            'npca_per_branch': 3,
                            'snippet_mask_radius': 250,
                            'scheme1_detect_channel_radius': None,  # 150, # the length around the channel with highest waveform amp to apply detect_time_radius_msec (None = applied infinitely so all channel are blocked -> bad; except if sorted by group)
                            'scheme2_phase1_detect_channel_radius': None,  # 200,
                            'scheme2_detect_channel_radius': 50,  # Not clear what to put here 
                            'scheme2_max_num_snippets_per_training_batch': 200,
                            'scheme2_training_duration_sec': 60 * 5,
                            'scheme2_training_recording_sampling_mode': 'uniform',
                            'scheme3_block_duration_sec': 60 * 30,
                            'freq_min': 300,
                            'freq_max': 6000,
                            'filter': False,
                            'whiten': True  # Important to do whitening
                                   },
                       'extractor' : si.read_npz_sorting  # se.MdaSortingExtractor
                       },
                       
    'spykingcircus2' : {'surname' : "SC2",
                        'docker_image' : None,
                        'params' :{
                                    "general": {"ms_before": 2, "ms_after": 2, "radius_um": 100},
                                    "sparsity": {"method": "ptp", "threshold": 0.25},
                                    "filtering": {"freq_min": 150},
                                    "detection": {"peak_sign": "both", "detect_threshold": 4},
                                    "selection": {
                                        "method": "smart_sampling_amplitudes",
                                        "n_peaks_per_channel": 5000,
                                        "min_n_peaks": 20000,
                                        "select_per_channel": False,
                                        "seed": 42,
                                                },
                                    "clustering": {"legacy": False},
                                    "matching": {"method": "circus-omp-svd"},
                                    "apply_preprocessing": True,
                                    "cache_preprocessing": {"mode": "memory", "memory_limit": 0.5, "delete_cache": True},
                                    "multi_units_only": False,
                                    "job_kwargs": {"n_jobs": 0.8},
                                    "debug": False,
                                    },
                        'extractor' : si.read_npz_sorting,  # se.SpykingCircusSortingExtractor # NpzSortingExtractor (might be this one instead)
                        'path' : os.path.join('sorter_output', 'sorting')
                        },
    
    'tridesclous2' : {'surname' : "TDC2",
                        'docker_image' : None,
                        'params' :{
                                    "apply_preprocessing": False,
                                    "cache_preprocessing": {"mode": "memory", "memory_limit": 0.5, "delete_cache": True},
                                    "waveforms": {
                                        "ms_before": 0.5,
                                        "ms_after": 1.5,
                                        "radius_um": 120.0,
                                    },
                                    "filtering": {"freq_min": 300.0, "freq_max": 12000.0},
                                    "detection": {"peak_sign": "both", "detect_threshold": 5, "exclude_sweep_ms": 1.5, "radius_um": 150.0},
                                    "selection": {"n_peaks_per_channel": 5000, "min_n_peaks": 20000},
                                    "svd": {"n_components": 6},
                                    "clustering": {
                                                    "split_radius_um": 40.0,
                                                    "merge_radius_um": 40.0,
                                                    "threshold_diff": 1.5,
                                                },
                                    "templates": {
                                                    "ms_before": 2.0,
                                                    "ms_after": 3.0,
                                                    "max_spikes_per_unit": 400,
                                                    # "peak_shift_ms": 0.2,
                                                },
                                    # "matching": {"method": "tridesclous", "method_kwargs": {"peak_shift_ms": 0.2, "radius_um": 100.0}},
                                    "matching": {"method": "circus-omp-svd", "method_kwargs": {}},
                                    "job_kwargs": {"n_jobs": -1},
                                    "save_array": True,
                                },
                        'extractor' : se.TridesclousSortingExtractor
                        }    
    }