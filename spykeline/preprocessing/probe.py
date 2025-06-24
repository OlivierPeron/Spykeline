from probeinterface import ProbeGroup, generate_multi_shank, generate_tetrode, get_probe
from probeinterface.plotting import plot_probegroup

import numpy as np
from ..config import home_probes

def create_probe(metadata) -> ProbeGroup:
    """
    Parameters
    ----------
    metadata : dict
        Dict with metadata, mostly used for probe creation.

    Returns
    -------
    probegroup : ProbeGroup
        The final ensemble of probes that were used to record.
    """
    from .. import spykeparams

    probegroup = ProbeGroup()
    shanks_groups = []

    sh_offset = 0
    ch_offset = 0
    probe_id = 0

    new_probe_dict = {}

    for group_id, probe_info in metadata['Probes'].items():
        brand = probe_info['Brand']
        model = probe_info['Model']

        group_id = int(group_id)

        probe_ch = metadata['Anatomical_groups'][group_id]

        if model in home_probes.keys(): # HOME PROBES
            if model == 'Tetrode':
                nb_shanks = len(probe_ch) // 4
                if nb_shanks > 1:
                    for tetrode_id in range(nb_shanks):
                        # Handle metadata
                        ## Shanks
                        shanks = home_probes[model]['shanks']
                        shanks_groups.append([x + sh_offset + tetrode_id for x in shanks])
                        ## Channel map
                        probe_map = [x + ch_offset + 4*tetrode_id for x in home_probes[model]['map']]

                        # Create the probe
                        probe = generate_tetrode()
                        probe.move([2800 *(probe_id + tetrode_id), 0])
                        probe.set_device_channel_indices(probe_ch[tetrode_id*4:(tetrode_id+1)*4])
                        probegroup.add_probe(probe)

                        new_probe_dict[probe_id] = {
                            'Brand': brand,
                            'Model': model,
                            'Architecture': 'Default'
                        }

                        probe_id += 1
                else:
                    # Handle metadata
                    ## Shanks
                    shanks = home_probes[model]['shanks']
                    shanks_groups.append([x + sh_offset  for x in shanks])
                    ## Channel map
                    probe_map = [x + ch_offset for x in home_probes[model]['map']]

                    # Create the probe
                    probe = generate_tetrode()
                    probe.move([2800 * probe_id, 0])
                    probe.set_device_channel_indices(probe_ch)
                    probegroup.add_probe(probe)
                    new_probe_dict[probe_id] = {
                            'Brand': brand,
                            'Model': model,
                            'Architecture': 'Default'
                        }
                    probe_id += 1
            else :
                # Handle metadata
                ## Shanks
                shanks = home_probes[model]['shanks']
                nb_shanks = len(set(shanks))
                shanks_groups.append([x + sh_offset for x in shanks])
                ## Channel map
                probe_map = [x + ch_offset for x in home_probes[model]['map']]
                
                assert sorted(probe_map) == sorted(probe_ch), f"Probe {probe_id} channel map does not match the probe map. Please check the metadata."

                # Create the probe
                probe = generate_multi_shank(num_shank=nb_shanks,
                                             num_columns=2,
                                             num_contact_per_column= 4,
                                             xpitch=20,
                                             ypitch=20,
                                             y_shift_per_column=[-10, 0])

                probe.move([2800 * probe_id, 0])
                probe.set_device_channel_indices(probe_ch)
                probegroup.add_probe(probe)
                metadata['Probes'][probe_id]['Architecture'] = 'Default'

                if shanks.count(0)//2 >= 6:
                    new_probe_dict[probe_id] = {
                            'Brand': brand,
                            'Model': model,
                            'Architecture': 'Linear'
                        }
                else:
                    new_probe_dict[probe_id] = {
                            'Brand': brand,
                            'Model': model,
                            'Architecture': 'Default'
                        }

                probe_id += 1
        else:
            # Create the probe
            probe = get_probe(manufacturer=brand,
                              probe_name=model)

            if len(probe_ch) == 32:
                headstage = 'RHD2132'
            elif len(probe_ch) == 64:
                headstage = 'RHD2164'
            else:
                raise ValueError(f"Probe {probe_id} has an unknown number of channels. Update the script for this new case.")
            
            from probeinterface.wiring import get_available_pathways
            pathways = get_available_pathways()
            connector = None
            for pathway in pathways:
                con, _ = pathway.split('>')
                if con in model:
                    connector = con
                    break
            
            if connector is None:
                raise ValueError(f"Probe {probe_id} has an unknown connector. Update the script for this new case.")
            
            wiring = f"{connector}>{headstage}"

            assert wiring in pathways, f"Probe {probe_id} has an unknown wiring. Update the script for this new case by adding your probe in home_probes."

            probe.wiring_to_device(wiring)
            
            probe.move([2800 * probe_id, 0])

            probe.set_device_channel_indices(probe_ch)
            probegroup.add_probe(probe)

            if shanks.count(0)//2 >= 6:
                new_probe_dict[probe_id] = {
                        'Brand': brand,
                        'Model': model,
                        'Architecture': 'Linear'
                    }
            else:
                new_probe_dict[probe_id] = {
                        'Brand': brand,
                        'Model': model,
                        'Architecture': 'Default'
                    }

            probe_id += 1

            ## Shanks
            shanks = [x + ch_offset for x in probe.shank_ids.astype(int).tolist()]
            nb_shanks = len(set(shanks))
            shanks_groups.append([x + sh_offset for x in shanks])
            ## Channel map
            probe_map = probe.device_channel_indices.tolist()

        sh_offset += nb_shanks
        ch_offset += len(probe_map)

    # Plot probe
    if spykeparams["general"]["plot_probe"]:
        plot_probegroup(probegroup, same_axes = False, with_device_index=True)

    metadata['Probes'] = new_probe_dict

    return probegroup, shanks_groups, metadata