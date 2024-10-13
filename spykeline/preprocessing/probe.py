import pandas as pd

from probeinterface import Probe, ProbeGroup, generate_multi_shank, generate_tetrode, get_probe

from .. import spykeparams
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

    assert len(metadata['Anatomical_groups']) == len(metadata['Probes'])

    probegroup = ProbeGroup()

    for probe_index, probe_info in enumerate(metadata['Probes']):
        brand, model = probe_info.split('_')
        probe_ids = metadata['Anatomical_groups'][probe_index]

        shanks_for_probe = [shank for shank in metadata['Shanks_groups'] if any(electrode in probe_ids for electrode in shank)]

        if model in home_probes:

            if model == 'Tetrode':
                probe = generate_tetrode()
                probe.move([2800 * probe_index, 0])

            else :
                if spykeparams['spikesorting']['sorter'] == 'kilosort4': # Kilosort4 needs the probes to be on top of each other, instead than next to each other
                    probe = Probe(ndim=2, si_units='um')
                    positions = []
                    contact_ids = []
                    
                    for shank_index, shank in enumerate(shanks_for_probe):
                        for rank, electrode in enumerate(shank):
                            contact_ids.append(electrode)
                            positions.append((2800 * probe_index + 40 * (rank % 2),
                                              200 * shank_index + 20 * rank))
                            
                    probe.set_contacts(positions)
                    probe.set_device_channel_indices(contact_ids)
                    
                    df = pd.DataFrame(positions)
                    xmin, xmax = df[0].min(), df[0].max()
                    ymin, ymax = df[1].min(), df[1].max()
                    
                    polygon = [(xmin - 20, ymax + 20),              # Upper left corner
                               (xmin - 20, ymin - 20),              # Lower left corner
                               ((xmax + xmin) / 2, ymin - 100),     # Lower center tip
                               (xmax + 20, ymin - 20),              # Lower right corner
                               (xmax + 20, ymax + 20)]              # Upper right corner
                    
                    probe.set_planar_contour(polygon)
                    
                else:
                    probe = generate_multi_shank(num_shank=len(shanks_for_probe),
                                                       num_columns=2,
                                                       num_contact_per_column=len(shanks_for_probe[0]) // 2,
                                                       xpitch=20,
                                                       ypitch=20,
                                                       y_shift_per_column=[-10, 0])

                    probe.move([2800 * probe_index, 0])
        else:
            probe = get_probe(manufacturer=brand,
                              probe_name=model)
            probe.move([2800 * probe_index, 0])
            
        contact_ids = [channel for grp in shanks_for_probe for channel in grp]
        probe.set_device_channel_indices(contact_ids)
        probegroup.add_probe()

    return probegroup