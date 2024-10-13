import pandas as pd

from probeinterface import Probe, ProbeGroup, generate_multi_shank


def create_probe(Anatomical_groups, Shanks_groups, sorter):
    """
    

    Parameters
    ----------
    Anatomical_groups : list
        Information about the probes.
    Shanks_groups : list
        Information about the shanks.
    sorter : str
        Temporary : needed as loon as kilosort4 doesn't process multi-shank probes

    Returns
    -------
    probegroup : probegroup
        The final ensemble of probes that were used to record.

    """
    probegroup = ProbeGroup()
    
    for probe_nb, probe_ids in enumerate(Anatomical_groups):

        # List of shanks for this probe
        shanks_pr = [x for x in Shanks_groups if any(i in probe_ids for i in x)] 
        
        if sorter == 'kilosort4':
            
            probe = Probe(ndim = 2, 
                            si_units = 'um')
            
            positions = []
            contact_ids = []
            
            for shank_nb, shank_pr in enumerate(shanks_pr):
                for rank, electrode in enumerate(shank_pr):
                    contact_ids.append(electrode)
                    positions.append((2800*probe_nb + 40*(rank%2),
                                        200*shank_nb + 20*(rank)))
                    
            probe.set_contacts(positions)
            probe.set_device_channel_indices(contact_ids)
            
            df = pd.DataFrame(positions)
            
            xmin, xmax = min(df[0]), max(df[0])
            ymin, ymax = min(df[1]), max(df[1])
            
            polygon = [(xmin - 20, ymax + 20),              # Upper left corner
                        (xmin - 20, ymin - 20),              # Lower left corner
                        ((xmax + xmin)/2, ymin - 100),       # Lower center tip
                        (xmax + 20, ymin - 20),              # Lower right corner
                        (xmax + 20, ymax + 20)]              # Upper right corner
            
            probe.set_planar_contour(polygon)
                
            probegroup.add_probe(probe)

        else:
            multi_shank = generate_multi_shank(num_shank = len(shanks_pr),
                                               num_columns = 2,
                                               num_contact_per_column = int(len(shanks_pr[0])/2),
                                               xpitch = 20,
                                               ypitch = 20,
                                               y_shift_per_column = [-10, 0])
        
            multi_shank.move([2800*probe_nb, 0])
            probegroup.add_probe(multi_shank)

    return probegroup