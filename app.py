from customtkinter import *
from file_manager import FileManager
from capture_system import CaptureSystem
from safe_io import SafeIO

import customtkinter as ctk
import glob
import numpy as np


class App(CTk):
    
    def __init__(self, title):

        super().__init__()

        ARDUINO_BOARD = "Genuino Uno"
        TIME_PRESS_BUTTON = 0 # Time (sec) to offset recording after pressing button. Default: 0
        self.labels = tuple()
        self.is_confirmed = False

        self.output_dir = os.path.join(os.path.abspath(""),"test_data")
        self.file_manager = FileManager(self.output_dir)
        self.capture_system = CaptureSystem(ARDUINO_BOARD, self.output_dir, TIME_PRESS_BUTTON) 
        self.safe_io = SafeIO()

        self.title(title)
        self.geometry('720x480')
        self.minsize(720,480)
        set_default_color_theme("green")
        
        folder_options = []
        for file in os.listdir(self.output_dir):
            file_path = os.path.join(self.output_dir, file)
            if os.path.isdir(file_path):
                folder_options.append(file)

        # Recording menu setup
        r_menu = Menu(self,"Record event data", (0,1))
        r_menu.place(relx = 0.02, rely = 0.02, relwidth = 0.56, relheight = 0.81)
        # Add components to recording menu
        self.input_task_frame = InputFrame(r_menu, "Task name:", 1, 0, False)
        self.record_mode_frame = RadioFrame(r_menu, "Choose recording mode:", ["Primitive","Continuous"], 1, 1)
        self.input_labels_frame = InputFrame(r_menu, "Input Labels (int) e.g. 1,2,3:", 2, 1, True)
        self.input_labels_frame.button._command = self.confirm_function
        self.select_primitive = ComboFrame(r_menu, "Choose primitive:", folder_options, 2, 0)
        run_button = Button(r_menu, "Run", 3, 0)
        run_button._command = self.run_function
        self.stop_button = Button(r_menu, "Stop", 3, 1)
        self.stop_button._state = ctk.DISABLED
        self.stop_button._command = self.stop_function

        # Processing menu setup
        p_menu = Menu(self, "Process event data", 0)
        p_menu.place(relx = 0.6, rely = 0.02, relwidth = 0.38, relheight = 0.81)
        # Add components to processing menu
        self.select_folder = ComboFrame(p_menu, "Choose folder:", folder_options, 2, 0)
        self.process_mode_frame = RadioFrame(p_menu, "Choose processing mode:", ["Folder", "All Files"], 1, 0)
        process_button = Button(p_menu, "Process", 3, 0)
        process_button._command = self.process_function

        # Recording menu setup
        self.output_text = CTkTextbox(self, font = ("Arial",12), state = "disabled")
        self.output_text.place(relx = 0.02, rely = 0.85, relwidth = 0.96, relheight = 0.12)
        self.print_message("--------- OUTPUT TERMINAL ---------\n")

        self.mainloop()

    def print_message(self, message):
        self.output_text.configure(state = "normal")
        self.output_text.insert(ctk.END,message)
        self.output_text.see(ctk.END)
        self.output_text.configure(state = "disabled")

    def process_function(self):
        
        if self.process_mode_frame.radio_button1_enabled:
            
            folder = self.select_folder.get_current_value()

            list_all_files = glob.glob(os.path.join(self.output_dir,folder,"*.aedat"))
            for file in list_all_files:
                file_dir_no_ext = file[:len(file)-6] # Remove .aedat from file name
                self.file_manager.aedat_to_npy(file_dir_no_ext)

            self.print_message(f"Finished processing {len(list_all_files)} file(s) in the {folder} folder\n")

        else:

            list_all_files = glob.glob(os.path.join(self.output_dir,"**","*.aedat"),recursive=True)
            
            for file in list_all_files:
                file_dir_no_ext = file[:len(file)-6] # Remove .aedat from file name
                self.file_manager.aedat_to_npy(file_dir_no_ext)

            self.print_message(f"Finished processing all {len(list_all_files)} available .aedat files\n")

    def run_function(self):
        
        task_name = self.input_task_frame.input_text.get()

        if task_name == "":
            self.print_message(f"Please insert a task name \n")

        try:
            self.capture_system._start_serial_thread()
        except OSError as e:
            self.print_message(f"{str(e)}\n")
            raise

        self.stop_button._state = ctk.NORMAL
        self.capture_system._file_name = task_name.encode()

        if self.record_mode_frame.radio_button1_enabled: # Primitive
            with_labels = False
            primitive = self.select_primitive.get_current_value()
            list_existing_files = glob.glob(os.path.join(self.output_dir,primitive,f"{task_name}_*.aedat"))
            current_attempt = len(list_existing_files) + 1

        else: # Continuous
            with_labels = True
            list_existing_files = glob.glob(os.path.join(self.output_dir,f"{task_name}_*.aedat"))
            current_attempt = len(list_existing_files) + 1
            primitive = None

        while True:  
            try: 
                [final_times_list,first_ts,csv_file_dir] = self.capture_system.recording_function(current_attempt, task_name, primitive)
            except Exception as e:
                self.print_message(str(e))
                raise
            else:
                self.print_message(f"Recording duration: {(self.capture_system._stop_time-self.capture_system.start_time):.2f} seconds")
                current_attempt += 1
                self.write_csv_file_app(final_times_list, first_ts, csv_file_dir, with_labels)
                self.capture_system._wait_for_button_input("red","Press the Red Button to continue or the White Button to quit.", 200, 10, True)
        
    def confirm_function(self):
        
        temp_labels = self.input_labels_frame.input_text.get()

        try:
            self.labels = list(map(int, temp_labels.split(",")))
        except ValueError:
            self.print_message("Inserted non-integer labels\n")
            raise ValueError("Inserted non-integer labels")
        
        self.print_message(f"Labels were set\n")
        self.is_confirmed = True

    def stop_function(self):
        self.capture_system._close_capture_system()
        self.stop_button._state = ctk.DISABLED
        self.print_message(f"Stopped capturing\n")

    def write_csv_file_app(self,timestamp_list:list[int],first_ts:int,csv_file_dir:str,with_labels:bool) -> None:
        
        """
        Write timestamps and labels to .csv file
        """

        if not with_labels:
            times_csv = [[timestamp_list[0]*(10**6)+first_ts, timestamp_list[-1]*(10**6)+first_ts]]
            np.savetxt(csv_file_dir, times_csv, delimiter = ", ", fmt = ["%d","%d"])
        
        else:
            times_csv = []
            n_labels = len(timestamp_list)//2
            
            while len(self.labels) != n_labels:
                if self.is_confirmed:
                    self.print_message(f"{len(self.labels)} label(s) and {n_labels} time(s). Please insert correct amount of label(s):")
                    self.is_confirmed = False

            for i in range(n_labels):
                times_csv.append([self.labels[i],timestamp_list[2*i]*(10**6)+first_ts, timestamp_list[(2*i)+1]*(10**6)+first_ts])
            np.savetxt(csv_file_dir, times_csv, delimiter = ", ", fmt = ["%d","%d","%d"])


class Button(CTkButton):

    def __init__(self, menu, title, r, c):
        CTkButton.__init__(self, master = menu, text = title)
        self.grid(row = r, column = c, ipadx = 5, ipady = 5)

class ComboFrame(CTkFrame):

    def __init__(self, menu, title, primitives, r, c):
        CTkFrame.__init__(self, master = menu, corner_radius = 0)

        self.label = CTkLabel(self, text = title, font = ("Arial",13))
        self.combo_box = CTkComboBox(self, values = primitives, state = "readonly")
        self.combo_box.set("idle")
    
        self.grid(row = r, column = c, sticky="nsew", padx = 10, pady = 10)
        self.label.pack(side="top", expand = True, pady = (15,0))
        self.combo_box.pack(side="top", expand = True, pady = (0,25))
    
    def get_current_value(self):
        return self.combo_box.get()    

    def change_state(self, enable):
        if enable:
            self.combo_box._state = ctk.NORMAL
        else:
            self.combo_box._state = ctk.DISABLED        

class InputFrame(CTkFrame):

    def __init__(self, menu, title, r, c, with_button):
        CTkFrame.__init__(self, master = menu, corner_radius = 0)

        self.label = CTkLabel(self, text = title, font = ("Arial",13))
        self.input_text = CTkEntry(self)
        
        self.grid(row = r, column = c, sticky="nsew", padx = 10, pady = 10)
        
        if with_button:
            self.button = CTkButton(self, text = "Confirm")
            self.label.pack(side="top", expand = True, pady = (5,0))
            self.input_text.pack(side="top", expand = True, pady = (0,5))
            self.button.pack(side="top", expand = True, pady = (0,10))
        else:
            self.label.pack(side="top", expand = True, pady = (20,0))
            self.input_text.pack(side="top", expand = True, pady = (0,20))
    
    def get_current_value(self):
        return self.input_text.get()    

    def change_state(self, enable):
        if enable:
            self.input_text._state = ctk.NORMAL
        else:
            self.input_text._state = ctk.DISABLED     

class RadioFrame(CTkFrame):

    def __init__(self, menu, title, text_options, r, c):
        CTkFrame.__init__(self, master = menu, corner_radius = 0)
        self.menu = menu
        self.radio_button1_enabled = True

        self.label = CTkLabel(self, text = title, font = ("Arial",13))
        self.radio_button1 = CTkRadioButton(self, text = text_options[0])
        self.radio_button2 = CTkRadioButton(self, text = text_options[1])
        self.radio_button1.select()
        self.radio_button1._command = self.fcn_radio1
        self.radio_button2._command = self.fcn_radio2

        self.grid(row = r, column = c, sticky="nsew", padx = 10, pady = 10)
        self.label.pack(side="top", expand = True)
        self.radio_button1.pack(side="top", expand = True)
        self.radio_button2.pack(side="top", expand = True, pady = (0,15))
    
    def fcn_radio1(self):
        self.radio_button2.deselect()
        self.radio_button1_enabled = True

    def fcn_radio2(self):
        self.radio_button1.deselect()
        self.radio_button1_enabled = False

class Menu(CTkFrame):

    def __init__(self, parent, title, cconfig):
        
        super().__init__(parent)
        self.place(x = 0, y = 0, relwidth = 1, relheight = 1)

        self.rowconfigure((0,3), weight = 1, uniform = "a")
        self.rowconfigure((1,2), weight = 3, uniform = "a")
        self.columnconfigure(cconfig, weight = 1, uniform = "a")

        title = CTkLabel(self, text = title, font = ("Arial",18))
        title.grid(row = 0, column = 0, columnspan = 2) 

if __name__ == "__main__":
    App('DAVIS Data Capture System')