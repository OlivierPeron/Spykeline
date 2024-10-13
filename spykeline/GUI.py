import os
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

from spykeline.spikesorting.sorter_params import sorter_dict
from spykeline.config import home_probes, default_parameters, parameters_description, repo_path

class SpykelineGUI:
    def __init__(self, parameters = default_parameters):
        # Style constants
        self.padx = self.pady = 7
        self.dx = 2
        self.sorter_width = 20
        self.ftype_width = 14
        self.cmr_width = 10

        # Data options
        self.opt_sorter = list(sorter_dict.keys())
        self.opt_ftype = ['butter', 'cheby1', 'cheby2', 'ellip', 'bessel']
        self.opt_cmr = ['median', 'average']

        # Initialize GUI elements
        self.root = Tk()
        self.input_path = None
        self.secondary_path = None
        # self.btn_run = None
        self.params = defaultdict(dict)
        self.probes = []

        self.var_plot = BooleanVar(value=parameters['general']['plot_probe'])
        self.var_phy = BooleanVar(value=parameters['general']['export_to_phy'])
        self.var_amr = BooleanVar(value=parameters['general']['amplifier_renamed'])
        self.var_cur = BooleanVar(value=parameters['general']['do_curation'])
        self.var_spath = BooleanVar(value=parameters['general']['secondary_path'])

        self.var_minf = IntVar(value=parameters['preprocessing']['filter']['freq_min'])
        self.var_maxf = IntVar(value=parameters['preprocessing']['filter']['freq_max'])
        self.var_ftype = StringVar(value=parameters['preprocessing']['filter']['type'])
        self.var_cmr = StringVar(value=parameters['preprocessing']['common_reference']['method'])

        self.var_sorter = StringVar(value=parameters['spikesorting']['sorter'])

        self.var_amp = IntVar(value=parameters['curation']['noise_amp_th'])
        self.var_dist = IntVar(value=parameters['curation']['distrib_th'])
        self.var_recursive = BooleanVar(value=parameters['curation']['recursive'])

    def select_folder(self, ent):
        folder_path = filedialog.askdirectory(title="Select a Folder")
        if folder_path:
            ent.delete(0, 'end')
            ent.insert(0, folder_path)

    def toggle_frame(self, var, frame, resize=False):
        if var.get():
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

    def run(self):
        # Collect values from GUI widgets
        self.params['general'] = {
            'plot_probe': self.var_plot.get(),
            'export_to_phy': self.var_phy.get(),
            'amplifier_renamed': self.var_amr.get(),
            'do_curation': self.var_cur.get(),
            'secondary_path': self.var_spath.get()
        }
        self.params['preprocessing'] = {
            'filter': {
                'freq_min': self.var_minf.get(),
                'freq_max': self.var_maxf.get(),
                'type': self.var_ftype.get()
            },
            'common_reference': {
                'method': self.var_cmr.get()
            }
        }
        self.params['spikesorting'] = {
            'sorter': self.var_sorter.get()
        }
        self.params['curation'] = {
            'noise_amp_th': self.var_amp.get(),
            'distrib_th': self.var_dist.get(),
            'recursive': self.var_recursive.get()
        }

        self.input_path = self.ent_ipath.get() 
        if self.params['general']['secondary_path']:
            self.secondary_path = self.ent_spath.get()

        var_nbp = int(self.ent_probe.get())
        
        for window_id in range(var_nbp):
            window = ProbeGUI(window_id + 1, var_nbp)
            self.probes.append(window.GUI())

        self.root.destroy()

    def enable_run_button(self):
        if self.btn_run:
            self.btn_run.config(state='normal')

    def check_paths(self):
        paths = defaultdict()
        all_paths_valid = True

        if self.ent_ipath.get().strip():
            paths['Input Path'] = self.ent_ipath.get()
        else:
            messagebox.showerror("Path Error", "You must specify an input path")
            all_paths_valid = False

        if self.var_spath.get():
            if self.ent_spath.get().strip():
                paths['Secondary Path'] = self.ent_spath.get()
            else:
                messagebox.showerror("Path Error", "Secondary path is enabled but not specified")
                all_paths_valid = False

        for path_name, path in paths.items():
            if not os.path.exists(path):
                messagebox.showerror("Path Error", f"The {path_name} does not exist: {path}")
                all_paths_valid = False

        if all_paths_valid:
            self.enable_run_button()

    def create_gui(self):
        self.root.title("SpykeLine")
        self.root.geometry("580x666+653+270")
        self.root.resizable(False, False)
        self.root.columnconfigure(1, weight=1)

        # Set the window icon
        self.root.iconbitmap('./spykeline/docs/logo.ico')

        ## Logo Canva
        self.img_logo = PhotoImage(file='./spykeline/docs/logo.png', master=self.root)

        self.frm_logo = Frame(self.root)
        self.cnv_logo = Canvas(self.frm_logo, width=500, height=150)
        self.cnv_logo.create_image(250, 80, image=self.img_logo)

        self.frm_logo.columnconfigure(0, weight=1)
        self.frm_logo.grid(row=0, column=0, columnspan=2, padx=self.padx, pady=self.pady)
        self.cnv_logo.grid(row=0, column=0, padx=self.padx, pady=self.pady)

        ## Paths frame
        self.frm_paths = LabelFrame(self.root, text='Input Paths')
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
        self.var_spath = BooleanVar()
        self.btn_spath = Checkbutton(self.frm_paths, 
                                     text="Secondary path", 
                                     variable=self.var_spath,
                                     command=lambda: self.toggle_frame(self.var_spath, self.frm_spath, resize=True))
        self.btn_spath.grid(row=2, column=1, columnspan=2, padx=self.padx, pady=self.pady)

        self.btn_cpath = Button(self.frm_paths, text='Check paths', command=lambda: self.check_paths())
        self.btn_cpath.grid(row=2, column=0, padx=self.padx, pady=self.pady)

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

        ## Sorter
        for ids, option in enumerate(self.opt_sorter):
            self.opt_sorter[ids] = option.ljust(self.sorter_width + self.dx)

        self.frm_sorter = LabelFrame(self.root, text='Sorter')
        self.frm_sorter.grid(row=2, column=0, padx=self.padx, pady=self.pady/2, sticky='nsew')
        self.frm_sorter.columnconfigure(0, weight=1)
        self.frm_sorter.columnconfigure(1, weight=0)
        self.frm_sorter.columnconfigure(2, weight=0)
        self.frm_sorter.columnconfigure(3, weight=1)

        self.lbl_sorter = Label(self.frm_sorter, text='Sorter selected')
        self.opm_sorter = OptionMenu(self.frm_sorter,
                                     self.var_sorter,
                                    *self.opt_sorter)
        self.opm_sorter.config(width=self.sorter_width)

        self.lbl_sorter.grid(row=0, column=1, padx=self.padx, pady=self.pady/2, sticky='e')
        self.opm_sorter.grid(row=0, column=2, padx=self.padx, pady=self.pady/2, sticky='w')

        ## Nb probes
        self.frm_probe = LabelFrame(self.root, text = 'Probe')
        self.frm_probe.grid(row=2, column=1, padx=self.padx, pady=self.pady/2, sticky='nsew')

        self.lbl_probe = Label(self.frm_probe, text = 'Number of probe')
        self.ent_probe = Entry(self.frm_probe)

        self.lbl_probe.grid(row=0, column=0, padx=self.padx, pady=self.pady, sticky='nsew')
        self.ent_probe.grid(row=0, column=1, padx=self.padx, pady=self.pady, sticky='nsew')

        ## Parameters frame
        self.frm_params = LabelFrame(self.root, text='Parameters')
        self.frm_params.grid(row=3, column=0, columnspan=2, padx=self.padx, pady=self.pady/2, sticky='nsew')
        self.frm_params.config(width=800)

        self.frm_params.rowconfigure(0, weight=0)
        self.frm_params.rowconfigure(1, weight=0)
        self.frm_params.rowconfigure(2, weight=1)

        self.frm_params.columnconfigure(0, weight=0)
        self.frm_params.columnconfigure(1, weight=1)
        self.frm_params.columnconfigure(2, weight=0)

        ## General parameters
        # plot probes
        self.btn_plot = Checkbutton(self.frm_params, 
                                    text="Plot probes", 
                                    variable=self.var_plot)
        self.btn_plot.grid(row=0, column=0, sticky='w', pady=self.pady/2, padx=self.padx)

        # export to phy
        self.btn_phy = Checkbutton(self.frm_params, 
                                   text="Export to phy", 
                                   variable=self.var_phy)
        self.btn_phy.grid(row=0, column=1, sticky='w', pady=self.pady/2, padx=self.padx)

        # amplifier renamed
        self.btn_amr = Checkbutton(self.frm_params, 
                                   text="Amplifier renamed", 
                                   variable=self.var_amr)
        self.btn_amr.grid(row=1, column=0, sticky='w', pady=self.pady/2, padx=self.padx)

        # do curation
        self.btn_cur = Checkbutton(self.frm_params, 
                                   text="Do curation", 
                                   variable=self.var_cur,
                                command=lambda: self.toggle_frame(self.var_cur, self.frm_cur))
        self.btn_cur.grid(row=1, column=1, sticky='w', pady=self.pady/2, padx=self.padx) 

        ## Curation    
        self.frm_cur = LabelFrame(self.frm_params, text='Curation')
        self.frm_cur.grid(row=2, column=0, columnspan=2, padx=self.padx, pady=self.pady/2, sticky='nsew')

        self.btn_recursive = Checkbutton(self.frm_cur, text="Recursive", variable=self.var_recursive)
        self.lbl_amp = Label(self.frm_cur, text='Amplitude threshold')
        self.ent_amp = Entry(self.frm_cur, textvariable=self.var_amp)
        self.lbl_dist = Label(self.frm_cur, text='Distribution threshold')
        self.ent_dist = Entry(self.frm_cur, textvariable=self.var_dist)

        self.btn_recursive.grid(row=0, column=0, sticky='w', pady=self.pady/2)
        self.lbl_amp.grid(row=1, column=0, sticky='w', padx=self.padx/2, pady=self.pady)
        self.ent_amp.grid(row=1, column=1, sticky='w', padx=self.padx/2, pady=self.pady)
        self.lbl_dist.grid(row=2, column=0, sticky='w', padx=self.padx/2, pady=self.pady)
        self.ent_dist.grid(row=2, column=1, sticky='w', padx=self.padx/2, pady=self.pady)

        ## Preprocessing
        self.frm_prepro = LabelFrame(self.frm_params, text='Preprocessing') 
        self.frm_prepro.grid(row=0, rowspan=3, column=2, columnspan=2, padx=self.padx, pady=self.pady/2, sticky='nsew')

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

        ## Buttons
        self.frm_buttons = Frame(self.root)
        self.frm_buttons.columnconfigure(0, weight=1)
        self.frm_buttons.columnconfigure(1, weight=1)
        self.frm_buttons.columnconfigure(2, weight=1)

        self.btn_help = Button(self.frm_buttons, text='Help', command=self.show_help)   
        self.btn_run = Button(self.frm_buttons, text='Run', command=self.run, state='disabled')

        self.frm_buttons.grid(row=4, column=0, columnspan=2, sticky='nsew', padx=self.padx, pady=self.pady)
        self.btn_help.grid(row=0, column=0, sticky='ew', padx=self.padx, pady=self.pady)
        self.btn_run.grid(row=0, column=2, sticky='ew', padx=self.padx, pady=self.pady) 


    def GUI(self):

        self.create_gui()
        self.root.mainloop()

        return self.params, self.input_path, self.secondary_path, self.probes
    
class ProbeGUI:
    def __init__(self, window_id, nb_probe):
        self.padx = self.pady = 7
        self.dx = 2

        self.id = window_id
        self.nb_probe = nb_probe
        self.root = Tk()

        self.probe_info = None

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

    def update_models(self):
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
            menu.add_command(label=model, command=lambda value=model: self.var_models.set(value))

        # self.opm_model.update()

    def forward(self):
        self.probe_info = f'{self.var_brands.get().strip()}_{self.var_models.get().strip()}'

        self.root.quit()
        self.root.destroy()

    def display(self):
        canva_width = 440
        canva_height = 300

        brand = self.var_brands.get().strip()
        model = self.var_models.get().strip()

        if model in home_probes:
            img_path = os.path.join('./spykeline/docs/probes', brand, model + '.png')
        else:
            img_path = os.path.join(repo_path, brand, model, model + '.png')

        try:
            # Load the image using Pillow (PIL)
            pil_image = Image.open(img_path)

            # Resize the image to fit the canvas size
            pil_image_resized = pil_image.resize((canva_width, canva_height), Image.ANTIALIAS)

            # Convert the resized image back to a Tkinter-compatible image
            self.img_model = ImageTk.PhotoImage(pil_image_resized, master=self.root)

            # If canvas already exists, delete its content before adding new image
            if hasattr(self, 'cnv_model'):
                self.cnv_model.delete("all")  # Clear any existing content in the canvas
            else:
                # Create the canvas only once
                self.cnv_model = Canvas(self.root, width=canva_width, height=canva_height)
                self.cnv_model.grid(row=2, column=0, columnspan=2, padx=self.padx, pady=self.pady, sticky='ns')
                
                # Configure the row 2 (3rd row) dynamically only when the image is shown
                self.root.rowconfigure(2, weight=1)

            # Add the image to the canvas
            self.cnv_model.create_image(0, 0, anchor='nw', image=self.img_model)

        except FileNotFoundError:
            print(f"Image not found: {img_path}")
            # If the image is not found, you can clear the canvas (optional)
            if hasattr(self, 'cnv_model'):
                self.cnv_model.delete("all")  # Clear any existing content in the canvas
                self.root.rowconfigure(2, weight=0)  # Collapse the empty row if no image is displayed

        # Update window size dynamically based on new image
        self.root.update_idletasks()
        current_width = self.root.winfo_width()
        new_height = self.root.winfo_reqheight()
        self.root.geometry(f"{current_width}x{new_height}")


    def create_gui(self):
        self.root.title("SpykeLine")
        self.root.geometry("480x245+653+270")
        self.root.resizable(False, False)
        self.root.rowconfigure(2, weight=0)
        self.root.columnconfigure(1, weight=1)

        # Set the window icon
        self.root.iconbitmap('./spykeline/docs/logo.ico')

        ## Logo Canva
        self.img_logo = PhotoImage(file='./spykeline/docs/logo.png', master=self.root)

        self.frm_logo = Frame(self.root)
        self.cnv_logo = Canvas(self.frm_logo, width=160, height=160)
        self.cnv_logo.create_image(80, 80, image=self.img_logo)

        self.frm_logo.columnconfigure(0, weight=1)
        self.frm_logo.grid(row=0, column=0, rowspan=2, padx=self.padx, pady=self.pady)
        self.cnv_logo.grid(row=0, column=0, padx=self.padx, pady=self.pady)

        # Probe id
        font_style = ('Helvetica', 14, 'bold')
        self.lbl_probe = Label(self.root, text=f'Probe {self.id}/{self.nb_probe}', font=font_style)
        self.lbl_probe.grid(row=0, column=1, padx=self.padx, pady=self.pady, sticky='ns')

        ## Probe Frame
        self.frm_probe = LabelFrame(self.root, text = 'Probe')

        self.lbl_brand = Label(self.frm_probe, text = 'Brand')
        self.opm_brand = OptionMenu(self.frm_probe, self.var_brands, *self.display_brands)
        self.opm_brand.config(width=self.opm_width + self.dx)

        self.lbl_model = Label(self.frm_probe, text = 'Model')
        self.opm_model = OptionMenu(self.frm_probe, self.var_models, *self.display_models[self.var_brands.get().strip()])
        self.opm_model.config(width=self.opm_width + self.dx)

        self.frm_probe.grid(row=1, column=1, padx=self.padx, pady=self.pady)
        
        self.lbl_brand.grid(row=0, column=0, padx=self.padx, pady=self.pady)
        self.opm_brand.grid(row=0, column=1, padx=self.padx, pady=self.pady)
        self.lbl_model.grid(row=1, column=0, padx=self.padx, pady=self.pady)
        self.opm_model.grid(row=1, column=1, padx=self.padx, pady=self.pady)

        # Trace the change in brand selection
        self.var_brands.trace_add('write', self.update_models)

        ## Buttons 
        # Display button
        self.btn_display = Button(self.root, text='Display', command=self.display)
        self.btn_display.grid(row=3, column=0, padx=self.padx, pady=self.pady, sticky='ns')

        # Forward button
        if self.id == self.nb_probe:
            self.btn_forward = Button(self.root, text='Run', command=self.forward)
        else:
            self.btn_forward = Button(self.root, text='Next >', command=self.forward)
        self.btn_forward.grid(row=3, column=1, padx=self.padx, pady=self.pady, sticky='ns')

    def GUI(self):
        self.create_gui()
        self.root.mainloop()

        return self.probe_info


if __name__ == "__main__":

    gui = SpykelineGUI()
    params, input_path, secondary_path, probe_list = gui.GUI()

    print("Params:", params)
    print("Input path:", input_path)
    print("Secondary path:", secondary_path)

    for probe_id, probe in enumerate(probe_list):
        print(f"Probe {probe_id} : {probe}")