import os
import json
import webbrowser
from PIL import Image, ImageTk

from collections import defaultdict
from tkinter import (
    Canvas,
    PhotoImage,
    LabelFrame,
    Label, 
    Entry,
    Button,
    BooleanVar,
    StringVar,
    OptionMenu,
    Toplevel,
    Text,
    Frame,
    Tk,
    Checkbutton,
    IntVar,
    messagebox,
    filedialog)

import spikeinterface.sorters as ss

from spykeline.spikesorting.sorter_params import sorter_dict
from spykeline.config import home_probes, default_parameters, parameters_description, repo_path
from spykeline.tools import read_rhd
from probeinterface import get_probe

class SpykelineGUI:

    metadata = defaultdict(list) # temp metadata to assert the proper selection of probes

    def __init__(self, parameters = default_parameters):
        # Style constants
        self.padx = self.pady = 7
        self.dx = 2
        self.ftype_width = 14
        self.cmr_width = 10

        # Data options
        self.opt_ftype = ['butter', 'cheby1', 'cheby2', 'ellip', 'bessel']
        self.opt_cmr = ['median', 'average']
        self.opt_EM = ['Local', 'Docker']

        self.sorters = {}
        self.sorters['Local'] = ss.installed_sorters()
        self.sorters['Docker'] = [sorter for sorter in sorter_dict.keys() if sorter_dict[sorter]['docker_image'] is not None]
        
        self.opm_width = max(
            max(len(engine) for engine in self.opt_EM),
            max(len(sorter) for engine in self.opt_EM for sorter in self.sorters[engine])
        ) 

        self.display_EM = [option.ljust(self.opm_width + self.dx) for option in self.opt_EM]
        self.display_sorters = self.sorters.copy()
        for mode in self.opt_EM:
            self.display_sorters[mode] = [option.ljust(self.opm_width + self.dx) for option in self.sorters[mode]]

        # Initialize GUI elements
        self.root = Tk()
        self.input_path = None
        self.secondary_path = None
        self.params = defaultdict(dict)
        self.disc_channels = StringVar()
        self.nb_probes = None
        self.probes = defaultdict(dict)
        self.has_probes = False
        self.display = BooleanVar(value=False)

        self.var_EM = StringVar(value=parameters['spikesorting']['execution_mode'])
        if 'kilosort4' in self.sorters[self.var_EM.get()]:
            ks4_ind = self.sorters[self.var_EM.get()].index('kilosort4')
            self.var_sorter = StringVar(value=self.sorters[self.var_EM.get()][ks4_ind])
        else:
            self.var_sorter = StringVar(value=self.sorters[self.var_EM.get()][0])

        self.var_plot = BooleanVar(value=parameters['general']['plot_probe'])
        self.var_phy = BooleanVar(value=parameters['general']['export_to_phy'])
        self.var_klu = BooleanVar(value=parameters['general']['export_to_klusters'])
        self.var_spiksort = BooleanVar(value=parameters['general']['do_spikesort'])
        self.var_cur = BooleanVar(value=parameters['general']['do_curation'])
        self.var_spath = BooleanVar(value=parameters['general']['secondary_path'])
        self.var_dat = BooleanVar(value=parameters['general']['save_dat'])

        self.var_minf = IntVar(value=parameters['preprocessing']['filter']['freq_min'])
        self.var_maxf = IntVar(value=parameters['preprocessing']['filter']['freq_max'])
        self.var_ftype = StringVar(value=parameters['preprocessing']['filter']['type'])
        self.var_cmr = StringVar(value=parameters['preprocessing']['common_reference']['method'])

        self.pipeline = StringVar(value=parameters['spikesorting']['pipeline'])

        self.var_recursive = BooleanVar(value=parameters['curation']['recursive'])
        self.var_noise = BooleanVar(value=parameters['curation']['remove_noise_units'])

    def select_folder(self, ent):
        folder_path = filedialog.askdirectory(title="Select a Folder")
        if folder_path:
            ent.delete(0, 'end')
            ent.insert(0, folder_path)

    def toggle_frame(self, var, frame, resize=False):

        var_map = {
            'spiksort': self.var_spiksort,
            'cur': self.var_cur
        }

        if isinstance(var, BooleanVar):
            if var.get():
                frame.grid()
            else:
                frame.grid_remove()
        elif isinstance(var, dict):
            grid = True
            for key, value in var.items():
                if var_map[key].get() != value:
                    grid = False
                
            if grid:
                frame.grid()
            else:
                frame.grid_remove()

        if resize:
            self.root.update_idletasks()
            current_width = self.root.winfo_width()
            new_height = self.root.winfo_reqheight()
            self.root.geometry(f"{current_width}x{new_height}")

    def open_url(self, url):
        try:
            webbrowser.open_new(url)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open the link. Error: {str(e)}")

    def show_help(self):
        self.help_window = Toplevel(self.root)
        self.help_window.title("Help")
        self.help_window.geometry("600x560+653+270")
        self.help_window.resizable(True, True)

        # Create a frame to hold the label
        frame = Frame(self.help_window)
        frame.pack(expand=True, fill='both', padx=10, pady=10)

        # Create a Label widget to display the help text
        help_info = ""
        for section, params in parameters_description.items():
            help_info += f"{section.capitalize()}:\n\n\n"
            if isinstance(params, dict):
                for param, description in params.items():
                    if isinstance(description, dict):
                        help_info += f"\n\t{param}:\n\n"
                        for sub_param, sub_description in description.items():
                            help_info += f"\t\t{sub_param}: {sub_description}\n\n"
                    else:
                        help_info += f"{param}: {description}\n\n"
            else:
                help_info += f"{params}\n"
            help_info += "\n"

        help_label = Text(frame, wrap='word', font=("TkDefaultFont", 10))
        help_label.pack(expand=True, fill='both')

        # Configure tags for bold text
        help_label.tag_configure("bold", font=("TkDefaultFont", 10, "bold"))

        # Apply bold formatting
        for line in help_info.split('\n'):
            if ':' in line:
                colon_index = line.index(':')
                help_label.insert('end', line[:colon_index], "bold")
                help_label.insert('end', line[colon_index:])
            else:
                help_label.insert('end', line + '\n')

        help_label.insert('end', 'GitHub Repository', 'link')
        
        # Configure tag for hyperlink
        help_label.tag_configure('link', foreground='blue', underline=True)
        help_label.tag_bind('link', '<Button-1>', lambda e: self.open_url("https://github.com/GirardeauLab/Spykeline"))
        help_label.tag_bind('link', '<Enter>', lambda e: help_label.config(cursor='hand2'))
        help_label.tag_bind('link', '<Leave>', lambda e: help_label.config(cursor=''))

    def show_popup(self, message):
        """Creates a pop-up window and returns the user's answer ('Yes' or 'No')."""
        popup = Toplevel(self.root)
        popup.title("Confirmation")
        popup.geometry("250x100+700+300")

        # Create a StringVar to store the user's choice
        user_response = StringVar()

        # Create a label with the message and a wraplength
        label = Label(popup, text=message, font=("TkDefaultFont", 10), wraplength=230)
        label.pack(pady=10)

        # Button functions to set response and close the window
        def on_yes():
            user_response.set("Yes")
            popup.destroy()

        def on_no():
            user_response.set("No")
            popup.destroy()

        # Create Yes and No buttons
        button_frame = Frame(popup)
        button_frame.pack(pady=5)

        yes_button = Button(button_frame, text="Yes", command=on_yes)
        yes_button.pack(side='left', padx=5)

        no_button = Button(button_frame, text="No", command=on_no)
        no_button.pack(side='right', padx=5)

        # Wait until the user selects an option
        popup.wait_window()

        return user_response.get()

    def run(self):
        if self.nb_probes == 1:
            running_mode = 'single'
        else:
            running_mode = 'multiple'
        # Collect values from GUI widgets
        self.params['general'] = {
            'plot_probe': self.var_plot.get(),
            'export_to_phy': self.var_phy.get(),
            'export_to_klusters': self.var_klu.get(),
            'do_spikesort': self.var_spiksort.get(),
            'do_curation': self.var_cur.get(),
            'secondary_path': self.var_spath.get(),
            'discard_channels': [int(channel.strip()) for channel in self.disc_channels.get().split(',')] if self.disc_channels.get() else [],
            'save_dat': self.var_dat.get(),
            'mode': running_mode
        }
        self.params['preprocessing'] = {
            'filter': {
                'freq_min': self.var_minf.get(),
                'freq_max': self.var_maxf.get(),
                'type': self.var_ftype.get()
            },
            'common_reference': {
                'method': self.var_cmr.get()
            },
            'whiten': False
        }
        self.params['spikesorting'] = {
            'folder:': self.ent_sort_path.get().strip(),
            'execution_mode': self.var_EM.get().strip(),
            'sorter': self.var_sorter.get().strip(),
            'pipeline': self.pipeline.get().strip()
        }
        self.params['curation'] = {
            'recursive': self.var_recursive.get(),
            'remove_noise_units': self.var_noise.get(),
        }

        self.input_path = self.ent_ipath.get() 
        if self.params['general']['secondary_path']:
            self.secondary_path = self.ent_spath.get()

        self.root.destroy()

        if not self.has_probes:     
            for window_id in range(self.nb_probes):
                window = ProbeGUI(window_id + 1, self.nb_probes, SpykelineGUI.metadata['Anatomical_groups'][window_id])
                self.probes[window_id] = window.GUI()

            with open(os.path.join(self.input_path, 'probes.json'), 'w') as f:
                json.dump(self.probes, f)

    def check_paths(self):

        paths = defaultdict()
        all_paths_valid = True

        # Check main path
        if self.ent_ipath.get().strip():
            paths['Input Path'] = self.ent_ipath.get()
        else:
            messagebox.showerror("Path Error", "You must specify an input path")
            all_paths_valid = False

        # Check Optional path 
        if self.var_spath.get():
            if self.ent_spath.get().strip():
                paths['Secondary Path'] = self.ent_spath.get()
            else:
                messagebox.showerror("Path Error", "Secondary path is enabled but not specified")
                all_paths_valid = False

        # Check sorting path
        if not (self.var_spiksort.get()) and self.var_cur.get():
            if self.ent_sort_path.get().strip():
                paths['Sorting'] = self.ent_sort_path.get()
            else:
                messagebox.showerror("Path Error", f"You have to give a path to your previous sorting's folder")
                all_paths_valid = False

        # check that the path exist
        for path_name, path in paths.items():
            if not os.path.exists(path):
                messagebox.showerror("Path Error", f"The {path_name} does not exist: {path}")
                all_paths_valid = False

        files = os.listdir(paths['Input Path'])
        if not any(file.endswith('.dat') for file in files):
                messagebox.showerror("Path Error", f"The .dat file is missing in the input path: {paths['Input Path']}")
                all_paths_valid = False

        # Check rhd or metadata:
        meta = True
        if not os.path.exists(os.path.join(paths['Input Path'], 'metadata.json')):
            meta = False
            if not any(file.endswith('rhd') for file in files):
                messagebox.showerror("Path Error", f"No .rhd file in the input path: {paths['Input Path']}, please provide it or have a metadata.json file")
                all_paths_valid = False

        if meta:
            with open(os.path.join(paths['Input Path'], 'metadata.json'), 'rb') as f:
                metadata = json.load(f)
                anat = metadata['Anatomical_groups'][:-1]
        else:
            rhd_path = os.path.join(paths['Input Path'], 'info.rhd')
            assert os.path.exists(rhd_path), "No xml file was found in the given in the input path"
            intan_info = read_rhd(rhd_path)
            anat = intan_info['Probe_channels']

        SpykelineGUI.metadata['Anatomical_groups'] = [list(map(int, probe)) for probe in anat]

        probe_file = os.path.join(paths['Input Path'], 'probes.json')
        if os.path.exists(probe_file):
            use_probe = self.show_popup(message = "A probe file was found in the input path. Do you want to use it?")
            if use_probe == 'Yes':
                self.has_probes = True
                with open(probe_file, 'r') as f:
                    tmp = json.load(f)
                self.probes = {int(key): value for key, value in tmp.items()}
            else:
                os.remove(probe_file)
                self.has_probes = False

        self.nb_probes = len(SpykelineGUI.metadata['Anatomical_groups'])

        if all_paths_valid:
            self.display.set(True)
            self.toggle_frame(self.display, self.frm_sorter, resize=True)
            self.toggle_frame(self.display, self.frm_params, resize=True)
            self.toggle_frame(self.display, self.frm_buttons, resize=True)

    def update_sorters(self):
        # Get the selected engine
        selected_engine = self.var_EM.get().strip()

        # Get the corresponding sorters for the selected engine
        sorters = self.display_sorters[selected_engine]

        # Update the sorter OptionMenu
        self.var_sorter.set(sorters[0])
        menu = self.opm_sorter['menu']
        menu.delete(0, 'end')

        # Insert new sorters into the menu
        for sorter in sorters:
            menu.add_command(label=sorter, command=lambda value = sorter: self.var_sorter.set(value))

    def create_gui(self):
        self.root.title("SpykeLine")
        self.root.geometry("580x320+653+270")
        self.root.resizable(False, False)
        self.root.columnconfigure(1, weight=1)


        #### LOGO ####
        # Set the window icon
        try:
            self.root.iconbitmap(os.path.join(os.path.dirname(__file__), 'docs', 'logo.ico'))
        except:
            self.root.iconbitmap(os.path.join(os.path.abspath(''), 'spykeline', 'docs', 'logo.ico'))

        ## Logo Canva
        try:
            self.img_logo = PhotoImage(file=os.path.join(os.path.dirname(__file__), 'docs', 'logo.png'), master=self.root)
        except:
            self.img_logo = PhotoImage(file=os.path.join(os.path.abspath(''), 'spykeline', 'docs', 'logo.png'), master=self.root)

        self.frm_logo = Frame(self.root)
        self.cnv_logo = Canvas(self.frm_logo, width=500, height=150)
        self.cnv_logo.create_image(250, 80, image=self.img_logo)

        self.frm_logo.columnconfigure(0, weight=1)
        self.frm_logo.grid(row=0, column=0, columnspan=2, padx=self.padx, pady=self.pady)
        self.cnv_logo.grid(row=0, column=0, padx=self.padx, pady=self.pady)


        #### PATHS ####
        ## Paths frame
        self.frm_paths = LabelFrame(self.root, text='Inputs')
        self.frm_paths.columnconfigure(1, weight=1)
        self.frm_paths.grid(row=1, column=0, columnspan=2, padx=self.padx, pady=self.pady/2, sticky='nsew')

        # Input path
        self.lbl_ipath = Label(self.frm_paths, text='Input folder')
        self.ent_ipath = Entry(self.frm_paths)
        self.btn_ipath = Button(self.frm_paths, text='Select folder', command=lambda: self.select_folder(self.ent_ipath))

        self.lbl_ipath.grid(row=0, column=0, padx=self.padx, pady=self.pady/2, sticky='w')
        self.ent_ipath.grid(row=0, column=1, padx=self.padx, pady=self.pady/2, sticky='ew')
        self.btn_ipath.grid(row=0, column=2, padx=self.padx, pady=self.pady/2, sticky='e')

        # Secondary path
        self.btn_spath = Checkbutton(self.frm_paths, 
                                     text="Secondary path", 
                                     variable=self.var_spath,
                                     command=lambda: self.toggle_frame(self.var_spath, self.frm_spath, resize=True))
        self.btn_spath.grid(row=4, column=1, columnspan=2, padx=self.padx, pady=self.pady)

        self.frm_spath = Frame(self.frm_paths)
        self.frm_spath.columnconfigure(1, weight=1)
        self.frm_spath.grid(row=1, column=0, columnspan=3, sticky='nsew')
        self.frm_spath.config(width=560)
        self.frm_spath.grid_remove()  # Initially hide the frame

        self.lbl_spath = Label(self.frm_spath, text="Secondary path")
        self.ent_spath = Entry(self.frm_spath)
        self.btn_spath_select = Button(self.frm_spath, text='Select folder', command=lambda: self.select_folder(self.ent_spath))

        self.lbl_spath.grid(row=0, column=0, padx=self.padx, pady=self.pady, sticky='w')
        self.ent_spath.grid(row=0, column=1, padx=self.padx, pady=self.pady, sticky='ew')
        self.btn_spath_select.grid(row=0, column=2, padx=self.padx, pady=self.pady, sticky='e')

        # Pipelines
        self.frm_skipspiksort = Frame(self.frm_paths)
        self.frm_skipspiksort.grid(row=3, column=0, columnspan=3, sticky='nsew')
        self.frm_skipspiksort.grid_remove()

        self.lbl_sort_path = Label(self.frm_skipspiksort, text='Sorting folder')
        self.ent_sort_path = Entry(self.frm_skipspiksort)
        self.btn_sort_ipath = Button(self.frm_skipspiksort, text='Select folder', command=lambda: self.select_folder(self.ent_sort_path))

        self.lbl_sort_path.grid(row=0, column=0, padx=self.padx, pady=self.pady/2, sticky='w')
        self.ent_sort_path.grid(row=0, column=1, padx=self.padx, pady=self.pady/2, sticky='ew')
        self.btn_sort_ipath.grid(row=0, column=2, padx=self.padx, pady=self.pady/2, sticky='e')

        self.lbl_opt_sorter = Label(self.frm_skipspiksort, text = 'Sorter')
        self.opm_opt_sorter = OptionMenu(self.frm_skipspiksort, self.var_sorter, *self.display_sorters[self.var_EM.get().strip()])
        self.opm_opt_sorter.config(width=self.opm_width + 4*self.dx)

        self.lbl_opt_sorter.grid(row=0, column=3, sticky='e', padx=self.padx, pady=self.pady)
        self.opm_opt_sorter.grid(row=0, column=4, sticky='e', padx=self.padx, pady=self.pady)

        self.btn_spiksort = Checkbutton(self.frm_paths, 
                                        text="Spikesorting", 
                                        variable=self.var_spiksort,
                                        command=lambda: self.toggle_frame({'spiksort': False, 'cur': True}, self.frm_skipspiksort, resize=True))
        self.btn_spiksort.grid(row=2, column=0, columnspan=2, padx=self.padx, pady=self.pady)

        self.btn_curat = Checkbutton(self.frm_paths, 
                                     text="Curation",
                                     variable=self.var_cur,
                                     command=lambda: self.toggle_frame({'spiksort': False, 'cur': True}, self.frm_skipspiksort, resize=True))
        self.btn_curat.grid(row=2, column=1, columnspan=2, padx=self.padx, pady=self.pady)

        self.btn_cpath = Button(self.frm_paths, text='Check paths', command=lambda: self.check_paths())
        self.btn_cpath.grid(row=4, column=0, padx=self.padx, pady=self.pady)

        #### SORTER ####
        self.frm_sorter = LabelFrame(self.root, text='Sorter')
        self.frm_sorter.grid(row=3, column=0, columnspan=2, padx=self.padx, pady=self.pady/2, sticky='nsew')

        ## ExecutionMode
        display_opt_EM = [option.ljust(self.cmr_width + self.dx) for option in self.opt_EM]

        self.lbl_EM = Label(self.frm_sorter, text='ExecutionMode')
        self.opm_EM = OptionMenu(self.frm_sorter, self.var_EM, *display_opt_EM)
        self.opm_EM.config(width=self.opm_width + 4*self.dx)

        ## Sorter
        self.lbl_sorter = Label(self.frm_sorter, text = 'Sorter')
        self.opm_sorter = OptionMenu(self.frm_sorter, self.var_sorter, *self.display_sorters[self.var_EM.get().strip()])
        self.opm_sorter.config(width=self.opm_width + 4*self.dx)

        self.lbl_EM.grid(row=0, column=0, sticky='w', padx=self.padx, pady=self.pady)
        self.opm_EM.grid(row=0, column=1, sticky='w', padx=self.padx, pady=self.pady)
        self.lbl_sorter.grid(row=0, column=3, sticky='e', padx=self.padx, pady=self.pady)
        self.opm_sorter.grid(row=0, column=4, sticky='e', padx=self.padx, pady=self.pady)

        # Trace the change in engine selection
        self.var_EM.trace_add('write', self.update_sorters)
        self.toggle_frame(self.display, self.frm_sorter)

        #### SPYKEPARAMS ####
        ## Parameters frame
        self.frm_params = LabelFrame(self.root, text='Parameters')
        self.frm_params.grid(row=4, column=0, columnspan=2, padx=self.padx, pady=self.pady/2, sticky='nsew')
        self.frm_params.config(width=800)

        self.frm_params.rowconfigure(0, weight=0)
        self.frm_params.rowconfigure(1, weight=0)
        self.frm_params.rowconfigure(2, weight=0)
        self.frm_params.rowconfigure(3, weight=0)
        self.frm_params.rowconfigure(4, weight=1)

        self.frm_params.columnconfigure(0, weight=0)
        self.frm_params.columnconfigure(1, weight=1)
        self.frm_params.columnconfigure(2, weight=0)

        ## General parameters
        # Save Preprocessed Recording
        self.btn_dat = Checkbutton(self.frm_params,
                                     text="Save pre-proc rec",
                                     variable=self.var_dat)
        self.btn_dat.grid(row=0, column=0, sticky='w', pady=self.pady/2, padx=self.padx)

        # plot probes
        self.btn_plot = Checkbutton(self.frm_params,
                                    text="Plot probes", 
                                    variable=self.var_plot)
        self.btn_plot.grid(row=0, column=1, sticky='w', pady=self.pady/2, padx=self.padx)

        # export to phy
        self.btn_phy = Checkbutton(self.frm_params, 
                                   text="Export to phy", 
                                   variable=self.var_phy)
        self.btn_phy.grid(row=1, column=0, sticky='w', pady=self.pady/2, padx=self.padx)

        # export to klusters
        self.btn_klu = Checkbutton(self.frm_params,
                                   text="Export to klusters",
                                   variable=self.var_klu)
        self.btn_klu.grid(row=1, column=1, sticky='w', pady=self.pady/2, padx=self.padx)

        # discard channels
        self.lbl_channels = Label(self.frm_params, text='Channels to discard:')
        self.ent_channels = Entry(self.frm_params, textvariable = self.disc_channels)

        self.lbl_channels.grid(row=3, column=0, padx=self.padx, pady=self.pady/2, sticky='w')
        self.ent_channels.grid(row=3, column=1, padx=self.padx, pady=self.pady/2, sticky='w')

        ## Curation    
        self.frm_cur = LabelFrame(self.frm_params, text='Curation')
        self.frm_cur.grid(row=4, column=0, columnspan=2, padx=self.padx, pady=self.pady/2, sticky='nsew')

        self.btn_recursive = Checkbutton(self.frm_cur, text="Recursive", variable=self.var_recursive)
        self.btn_noise = Checkbutton(self.frm_cur, text="Delete noise units", variable=self.var_noise)

        self.btn_recursive.grid(row=0, column=0, sticky='w', padx=self.padx, pady=self.pady/2)
        self.btn_noise.grid(row=0, column=1, sticky='w', padx=self.padx*6, pady=self.pady/2)

        self.toggle_frame(self.var_cur, self.frm_cur)

        ## Preprocessing
        self.frm_prepro = LabelFrame(self.frm_params, text='Preprocessing') 
        self.frm_prepro.grid(row=0, rowspan=5, column=2, columnspan=2, padx=self.padx, pady=self.pady/2, sticky='nsew')

        # Common reference
        display_opt_cmr = [option.ljust(self.cmr_width + self.dx) for option in self.opt_cmr]

        self.frm_cmr = Frame(self.frm_prepro)
        self.frm_cmr.grid(row=0, column=0, sticky='nsew', padx=self.padx, pady=self.pady)

        self.lbl_cmr = Label(self.frm_cmr, text='Common reference')
        self.opm_cmr = OptionMenu(self.frm_cmr, self.var_cmr, *display_opt_cmr)
        self.opm_cmr.config(width=self.cmr_width)

        self.lbl_cmr.grid(row=0, column=0, sticky='w', padx=self.padx, pady=self.pady)
        self.opm_cmr.grid(row=0, column=1, sticky='w', padx=self.padx, pady=self.pady)

        # Filter
        display_opt_ftype = [option.ljust(self.ftype_width + self.dx) for option in self.opt_ftype]

        self.frm_filter = LabelFrame(self.frm_prepro, text='Filter')
        self.frm_filter.grid(row=1, column=0, sticky='nsew', padx=self.padx, pady=self.pady/2)

        self.lbl_minf = Label(self.frm_filter, text='Min frequency')
        self.ent_minf = Entry(self.frm_filter, textvariable=self.var_minf)
        self.lbl_maxf = Label(self.frm_filter, text='Max frequency')
        self.ent_maxf = Entry(self.frm_filter, textvariable=self.var_maxf)
        self.lbl_ftype = Label(self.frm_filter, text='Filter type')
        self.opm_ftype = OptionMenu(self.frm_filter, self.var_ftype, *display_opt_ftype)
        self.opm_ftype.config(width=self.ftype_width)

        self.lbl_minf.grid(row=0, column=0, sticky='w', padx=self.padx, pady=self.pady)
        self.ent_minf.grid(row=0, column=1, sticky='w', padx=self.padx, pady=self.pady)
        self.lbl_maxf.grid(row=1, column=0, sticky='w', padx=self.padx, pady=self.pady)
        self.ent_maxf.grid(row=1, column=1, sticky='w', padx=self.padx, pady=self.pady)
        self.lbl_ftype.grid(row=2, column=0, sticky='w', padx=self.padx, pady=self.pady)
        self.opm_ftype.grid(row=2, column=1, sticky='w', padx=self.padx, pady=self.pady)

        self.toggle_frame(self.display, self.frm_params)

        ## Buttons
        self.frm_buttons = Frame(self.root)
        self.frm_buttons.columnconfigure(0, weight=1)
        self.frm_buttons.columnconfigure(1, weight=1)
        self.frm_buttons.columnconfigure(2, weight=1)

        self.btn_help = Button(self.frm_buttons, text='Help', command=self.show_help)   
        self.btn_run = Button(self.frm_buttons, text='Run', command=self.run)

        self.frm_buttons.grid(row=5, column=0, columnspan=2, sticky='nsew', padx=self.padx, pady=self.pady)
        self.btn_help.grid(row=0, column=0, sticky='ew', padx=self.padx, pady=self.pady)
        self.btn_run.grid(row=0, column=2, sticky='ew', padx=self.padx, pady=self.pady) 

        self.toggle_frame(self.display, self.frm_buttons)

    def GUI(self):

        self.create_gui()
        self.root.mainloop()

        return self.params, self.input_path, self.secondary_path, self.probes


class ProbeGUI:
    def __init__(self, window_id, nb_probe, contacts):
        self.padx = self.pady = 7
        self.dx = 4

        self.id = window_id
        self.nb_probe = nb_probe
        self.root_pb = Tk()

        self.probe_info = None
        self.contacts = contacts

        # Probe caracteristics
        self.brands = [item for item in os.listdir(repo_path) if os.path.isdir(os.path.join(repo_path, item)) and item[0] != '.']
        
        self.models = {}

        for brand in self.brands:
            self.models[brand] = [item for item in os.listdir(os.path.join(repo_path, brand)) if os.path.isdir(os.path.join(repo_path, brand, item)) and item[0] != '.']

        if not 'neuronexus' in self.brands:
            self.brands.append('neuronexus')
            self.models['neuronexus'] = []
        
        self.models['neuronexus'].extend(['Buzsaki32', 'Buzsaki64L'])
        
        self.brands.append('Other')
        self.models['Other'] = ['Tetrode']

        self.opm_width = max(
            max(len(brand) for brand in self.brands),
            max(len(model) for brand in self.brands for model in self.models[brand])
        ) 

        self.display_brands = [option.ljust(self.opm_width + self.dx) for option in self.brands]
        self.display_models = self.models.copy()
        for brand in self.brands:
            self.display_models[brand] = [option.ljust(self.opm_width + self.dx) for option in self.models[brand]]

        self.var_brands = StringVar(value=self.display_brands[0])
        self.var_models = StringVar(value=self.display_models[self.display_brands[0].strip()][0])

    def update_models(self, *args):
        # Get the selected brand
        selected_brand = self.var_brands.get().strip()

        # Get the corresponding models for the selected brand
        models = self.display_models[selected_brand]

        # Update the model OptionMenu
        self.var_models.set(models[0])
        menu = self.opm_model['menu']
        menu.delete(0, 'end')

        # Insert new models into the menu
        for model in models:
            menu.add_command(label=model, command=lambda value = model: self.var_models.set(value))

    def forward(self):

        brand = self.var_brands.get().strip()
        model = self.var_models.get().strip()

        if model in home_probes:
            if model == 'Buzsaki32':
                if len(self.contacts) != 32:
                    messagebox.showerror("Error", "The number of contacts in the selected probe does not match the number of contacts in the XML file")
                    return
            elif model == 'Buzsaki64L':
                if len(self.contacts) != 64:
                    messagebox.showerror("Error", "The number of contacts in the selected probe does not match the number of contacts in the XML file")
                    return
            # elif model == 'Tetrode':
            #     if len(self.contacts)%4 != 0:
            #         messagebox.showerror("Error", "The number of contacts in the selected probe does not match the number of contacts in the XML file")
            #         return
        else:
            probe = get_probe(manufacturer=brand, 
                              probe_name=model)
            
            if probe.get_contact_count() != len(self.contacts):
                messagebox.showerror("Error", "The number of contacts in the selected probe does not match the number of contacts in the XML file")
                return

        self.probe_info = {'Brand': self.var_brands.get().strip(), 
                           'Model': self.var_models.get().strip()
                           }

        self.root_pb.quit()
        self.root_pb.destroy()

    def display(self):
        canva_width = 440
        canva_height = 300

        brand = self.var_brands.get().strip()
        model = self.var_models.get().strip()

        if model in home_probes:
            try:
                img_path = os.path.join(os.path.dirname(__file__), 'docs', 'probes', brand, model + '.png')
            except :
                img_path = os.path.join(os.path.abspath(''), 'spykeline', 'docs', 'probes', brand, model + '.png')
        else:
            img_path = os.path.join(repo_path, brand, model, model + '.png')

        try:
            # Load the image using Pillow (PIL)
            pil_image = Image.open(img_path)

            # Resize the image to fit the canvas size
            pil_image_resized = pil_image.resize((canva_width, canva_height), Image.LANCZOS)

            # Convert the resized image back to a Tkinter-compatible image
            self.img_model = ImageTk.PhotoImage(pil_image_resized, master=self.root_pb)

            # If canvas already exists, delete its content before adding new image
            if hasattr(self, 'cnv_model'):
                self.cnv_model.delete("all")  # Clear any existing content in the canvas
            else:
                # Create the canvas only once
                self.cnv_model = Canvas(self.root_pb, width=canva_width, height=canva_height)
                self.cnv_model.grid(row=0, column=3, rowspan=4, padx=self.padx, pady=self.pady, sticky='ns')
                
                # Configure the row 2 (3rd row) dynamically only when the image is shown
                self.root_pb.columnconfigure(2, weight=1)

            # Add the image to the canvas
            self.cnv_model.create_image(0, 0, anchor='nw', image=self.img_model)

        except FileNotFoundError:
            print(f"Image not found: {img_path}")
            # If the image is not found, you can clear the canvas (optional)
            if hasattr(self, 'cnv_model'):
                self.cnv_model.delete("all")  # Clear any existing content in the canvas
                self.root_pb.rowconfigure(2, weight=0)  # Collapse the empty row if no image is displayed

        # Update window size dynamically based on new image
        self.root_pb.update_idletasks()
        new_width = self.root_pb.winfo_reqwidth()
        new_height = self.root_pb.winfo_reqheight()
        self.root_pb.geometry(f"{new_width}x{new_height}")

    def create_gui(self):
        self.root_pb.title("SpykeLine")
        self.root_pb.geometry("290x280+653+270")
        self.root_pb.resizable(False, False)
        self.root_pb.rowconfigure(3, weight=0)

        # Set the window icon
        try:
            self.root_pb.iconbitmap(os.path.join(os.path.dirname(__file__), 'docs', 'logo.ico'))
        except:
            self.root_pb.iconbitmap(os.path.join(os.path.abspath(''), 'spykeline', 'docs', 'logo.ico'))

        ## Logo Canva
        try:
            self.img_logo = PhotoImage(file=os.path.join(os.path.dirname(__file__), 'docs', 'logo.png'), master=self.root_pb).subsample(2)
        except:
            self.img_logo = PhotoImage(file=os.path.join(os.path.abspath(''), 'spykeline', 'docs', 'logo.png'), master=self.root_pb).subsample(2)

        self.frm_logo = Frame(self.root_pb)
        self.cnv_logo = Canvas(self.frm_logo, width=80, height=80)
        self.cnv_logo.create_image(40, 40, image=self.img_logo)

        self.frm_logo.columnconfigure(0, weight=1)
        self.frm_logo.grid(row=0, column=0, rowspan=2, padx=self.padx, pady=self.pady)
        self.cnv_logo.grid(row=0, column=0, padx=self.padx, pady=self.pady)

        # Probe id
        font_style = ('Helvetica', 14, 'bold')
        self.lbl_probe = Label(self.root_pb, text=f'Probe {self.id}/{self.nb_probe}', font=font_style)
        self.lbl_probe.grid(row=0, column=1, padx=self.padx, pady=self.pady, sticky='nsew')

        # Probe contacts
        self.lbl_contacts = Label(self.root_pb, text= f'{len(self.contacts)} contacts')
        self.lbl_contacts.grid(row=1, column=1, padx=self.padx, pady=self.pady, sticky='nsew')

        ## Probe infos Frame
        self.frm_info = LabelFrame(self.root_pb, text = 'Information')

        self.lbl_brand = Label(self.frm_info, text = 'Brand')
        self.opm_brand = OptionMenu(self.frm_info, self.var_brands, *self.display_brands)
        self.opm_brand.config(width=self.opm_width + self.dx)

        self.lbl_model = Label(self.frm_info, text = 'Model')
        self.opm_model = OptionMenu(self.frm_info, self.var_models, *self.display_models[self.var_brands.get().strip()])
        self.opm_model.config(width=self.opm_width + self.dx)

        self.frm_info.grid(row=2, column=0, columnspan=2, padx=self.padx, pady=self.pady)
        
        self.lbl_brand.grid(row=0, column=0, padx=self.padx, pady=self.pady)
        self.opm_brand.grid(row=0, column=1, padx=self.padx, pady=self.pady)
        self.lbl_model.grid(row=1, column=0, padx=self.padx, pady=self.pady)
        self.opm_model.grid(row=1, column=1, padx=self.padx, pady=self.pady)

        # Trace the change in brand selection
        self.var_brands.trace_add('write', self.update_models)

        ## Buttons
        # Display button
        self.btn_display = Button(self.root_pb, text='Display', command=self.display)
        self.btn_display.grid(row=4, column=0, padx=self.padx, pady=self.pady, sticky='ns')

        # Forward button
        if self.id == self.nb_probe:
            self.btn_forward = Button(self.root_pb, text='Run', command=self.forward)
        else:
            self.btn_forward = Button(self.root_pb, text='Next >', command=self.forward)
        self.btn_forward.grid(row=4, column=1, padx=self.padx, pady=self.pady, sticky='ns')

    def GUI(self):
        self.create_gui()
        self.root_pb.mainloop()

        return self.probe_info


if __name__ == "__main__":

    gui = SpykelineGUI()
    params, input_path, secondary_path, probe_dict = gui.GUI()

    print("Params:", params)
    print("Input path:", input_path)
    print("Secondary path:", secondary_path)

    for probe_id, probe in probe_dict.items():
        print(f"Probe {probe_id} : {probe['Brand']} {probe['Model']}")

    # import numpy as np
    # window = ProbeGUI(1, 2, np.arange(64), 8)
    # probe = window.GUI()
