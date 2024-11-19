import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from PIL import Image, ImageTk
import send2trash
from send2trash import send2trash  # Add this at the top with other imports
import configparser
import zipfile
import shutil
import tempfile
import time
from datetime import datetime
import traceback
import threading

MODS_PATH = "Mods"
MOD_ICON = "mod.png"
CONFIG_PATH = "config.ini"
BACKUP_PATH = "Backups"
COLUMNS = ("Name", "Description", "Author", "Files")  # Use constants for column names

class ModManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hitman: Blood Money Mod Manager")
        
        # Load or create config file for game installation folder
        self.config = configparser.ConfigParser()
        self.load_or_create_config()
    
        self.create_widgets()
        self.mods = self.load_mods()  # Load mods after widgets are created

    def backup_files(self):
        """Creates a backup of the game's Scene folder."""
        if messagebox.askyesno("Backup", "Do you want to create a backup of the Scene folder?"):
            game_folder = self.config.get("Settings", "game_install_folder", fallback="")
            if not game_folder or not os.path.isdir(game_folder):
                error_msg = "Invalid game folder path. Please configure the correct path."
                self.handle_error(error_msg)
                return
    
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            backup_path = os.path.join(BACKUP_PATH, backup_name)
    
            try:
                with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as backup_zip:
                    scenes_folder = os.path.join(game_folder, "Scenes")
                    if not os.path.exists(scenes_folder):
                        raise FileNotFoundError(f"Scenes folder not found at {scenes_folder}")
    
                    for root, _, files in os.walk(scenes_folder):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, game_folder)
                            backup_zip.write(file_path, arcname)
    
                self.update_status(f"Backup created successfully: {backup_name}")
                messagebox.showinfo("Backup Complete", f"Backup created successfully: {backup_name}")
            except Exception as e:
                self.handle_error(f"An error occurred while creating the backup: {e}")
    
    def handle_error(self, error_msg):
        """Handle errors by logging, showing a message box, and updating the status bar."""
        with open("mod_manager_log.txt", "a") as log_file:
            log_file.write(f"{datetime.now()}: {error_msg}\n")
        messagebox.showerror("Error", error_msg)
        self.update_status(error_msg)
    
    def restore_backup(self):
        """Restore the backup to the game's Scene folder."""
        backup_file = filedialog.askopenfilename(
            initialdir=BACKUP_PATH,
            title="Select Backup to Restore",
            filetypes=[("ZIP files", "*.zip")]
        )
        
        if not backup_file:
            self.update_status("No backup selected for restoration.")
            return
    
        if not messagebox.askyesno("Restore Backup", "Are you sure you want to restore the backup? This will overwrite existing Scene files."):
            self.update_status("Backup restoration canceled by user.")
            return
    
        game_folder = self.config.get("Settings", "game_install_folder", fallback="")
        if not game_folder or not os.path.isdir(game_folder):
            self.handle_error("Invalid game folder path. Please configure the correct path.")
            return
    
        try:
            scene_folder = os.path.join(game_folder, "Scenes")
            with zipfile.ZipFile(backup_file, "r") as backup_zip:
                backup_zip.extractall(scene_folder)
            self.update_status("Backup restored successfully.")
            messagebox.showinfo("Restore Complete", "Backup restored successfully.")
        except Exception as e:
            self.handle_error(f"Failed to restore backup: {e}")

    def load_or_create_config(self):
        """Load or prompt for the game install directory if it doesn't exist in config."""
        if os.path.exists(CONFIG_PATH):
            self.config.read(CONFIG_PATH)
        else:
            self.prompt_for_game_folder()
    
    def prompt_for_game_folder(self):
        """Prompt user for game installation folder and save it in config."""
        game_folder = filedialog.askdirectory(title="Select Hitman: Blood Money Installation Folder")
        if game_folder:
            self.config["Settings"] = {"game_install_folder": game_folder}
            with open(CONFIG_PATH, "w") as configfile:
                self.config.write(configfile)
        else:
            messagebox.showwarning("Warning", "No game folder selected. Some features may not work.")

    def load_mods(self):
        print("Loading mods...")
        mods = []
        print(f"MODS_PATH: {MODS_PATH}")
        for root, dirs, files in os.walk(MODS_PATH):
            print(f"Checking directory: {root}")
            if root == MODS_PATH:
                print("Skipping main Mods folder")
                continue  # Skip the main Mods folder, only use subdirectories
            folder_name = os.path.basename(root)
            print(f"Processing mod folder: {folder_name}")
            mod_info = {"name": folder_name, "description": "", "author": "", "files": [], "path": root, "folder_name": folder_name}
            if "mod.txt" in files:
                mod_txt_path = os.path.join(root, "mod.txt")
                print(f"Found mod.txt: {mod_txt_path}")
                parsed_info = self.parse_mod_txt(mod_txt_path)
                mod_info.update(parsed_info)
                print(f"Parsed mod info: {mod_info}")
            else:
                print(f"No mod.txt found in {folder_name}")
            
            # Check for mod.png
            mod_image_path = os.path.join(root, "mod.png")
            if os.path.exists(mod_image_path):
                mod_info["image_path"] = mod_image_path
                print(f"Found mod image: {mod_image_path}")
            else:
                print(f"No mod.png found for {folder_name}")
            
            mods.append(mod_info)
            print(f"Loaded mod: {mod_info['name']}")
        
        print(f"Total mods loaded: {len(mods)}")
        return mods

    def parse_mod_txt(self, mod_txt_path):
        print(f"Parsing mod.txt: {mod_txt_path}")
        mod_info = {"name": "", "description": "", "author": "", "files": []}
        try:
            with open(mod_txt_path, "r", encoding="utf-8") as f:
                content = f.read()
            print(f"Raw content of mod.txt:\n{content}")
            
            lines = content.split("\n")
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    key, value = [part.strip() for part in line.split(":", 1)]
                    if key.lower() in ["name", "description", "author"]:
                        mod_info[key.lower()] = value
                        print(f"Parsed {key}: {value}")
                    else:  # This is a file mapping
                        mod_info["files"].append({"destination": key, "source": value})
                        print(f"Parsed file: {value} -> {key}")
            
            print(f"Parsed mod info: {mod_info}")
        except Exception as e:
            print(f"Error parsing mod.txt: {str(e)}")
            traceback.print_exc()
        
        return mod_info
    def create_widgets(self):
        tk.Label(self.root, text="Mod Manager for Hitman: Blood Money", font=("Arial", 14)).pack(pady=10)
        tk.Button(self.root, text="Install Mods", command=self.open_mod_menu).pack(pady=5)
        tk.Button(self.root, text="Backup Game Files", command=self.backup_files).pack(pady=5)
        tk.Button(self.root, text="Restore Backup", command=self.restore_backup).pack(pady=5)

    def open_mod_menu(self):
        self.mod_window = tk.Toplevel(self.root)
        self.mod_window.title("Select Mods to Install")
        self.mod_window.geometry("800x600")
        self.mod_window.bind("<F5>", lambda event: self.populate_mods_table())
		
        # Status Bar for program status and current operations
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = tk.Label(self.mod_window, textvariable=self.status_var, bd=1, relief="sunken", anchor="w")
        self.status_bar.pack(side="bottom", fill="x")
    
        # Left Sidebar for mod image
        self.sidebar_frame = tk.Frame(self.mod_window, width=200, height=600, bg="gray")
        self.sidebar_frame.pack(side="left", fill="y")
        self.sidebar_frame.pack_propagate(False)
    
        # Placeholder for mod image
        self.mod_image_label = tk.Label(self.sidebar_frame, text="No Image Available", bg="gray")
        self.mod_image_label.pack(pady=10, padx=10)
    
        # Right Frame for Table View and Buttons
        right_frame = tk.Frame(self.mod_window)
        right_frame.pack(side="right", fill="both", expand=True)
    
        # Treeview for mod list
        self.mods_table = ttk.Treeview(right_frame, columns=COLUMNS, show="headings", selectmode="extended")
        for col in COLUMNS:
            self.mods_table.heading(col, text=col, command=lambda _col=col: self.sort_table(_col))
            self.mods_table.column(col, width=150)
        self.mods_table.pack(fill="both", expand=True, padx=10, pady=10)
    
        # Display mod image on row selection
        self.mods_table.bind("<<TreeviewSelect>>", self.display_selected_mod_image)
    
        # Action buttons
        button_frame = tk.Frame(right_frame)
        button_frame.pack(pady=10)
    
        install_button = tk.Button(button_frame, text="Install Selected Mods", command=self.install_selected_mods)
        install_button.pack(side="left", padx=5)
    
        add_mod_button = tk.Button(button_frame, text="Add Mod...", command=self.add_mod)
        add_mod_button.pack(side="left", padx=5)
     
        explore_button = tk.Button(button_frame, text="Explore Mod Contents", command=self.explore_mod_contents)
        explore_button.pack(side="left", padx=5)
     
        delete_button = tk.Button(button_frame, text="Delete Selected Mod", command=self.delete_mod)
        delete_button.pack(side="left", padx=5)
    
        # Populate the table after it's created
        self.populate_mods_table()

    def display_selected_mod_image(self, event):
        selected_item = self.mods_table.selection()
        if selected_item:
            mod_name = self.mods_table.item(selected_item[0])["values"][0]
            for mod in self.mods:
                if mod["name"] == mod_name:
                    mod_path = mod["path"]
                    mod_image_path = os.path.join(mod_path, MOD_ICON)
                    if os.path.exists(mod_image_path):
                        self.update_sidebar_image(mod_image_path)
                    else:
                        self.mod_image_label.config(image="", text="No Image Found")  # Show placeholder text
                    break

    def update_sidebar_image(self, image_path):
        img = Image.open(image_path).resize((200, 200))
        self.mod_image = ImageTk.PhotoImage(img)
        self.mod_image_label.config(image=self.mod_image, text="")

    def sort_table(self, col):
        """Sort the mod table by a selected column, toggling ascending/descending order."""
        try:
            self.sort_asc = not getattr(self, 'sort_asc', True)
            mods = [(self.mods_table.set(k, col), k) for k in self.mods_table.get_children("")]
            mods.sort(reverse=not self.sort_asc)
            for index, (val, k) in enumerate(mods):
                self.mods_table.move(k, "", index)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to sort table:\n{e}")

    def install_mod_file(self, source, destination, mod_folder):    											   
        print(f"Installing mod file: {source}")
        try:
            # Update status for the current file
            self.update_status(f"Installing {os.path.basename(source)}...")
    
            # Check for executable files and warn the user
            if source.lower().endswith((".exe", ".dll", ".bat", ".cmd", ".sh", ".scr", ".lnk", ".pif", ".cpl", ".sys", ".vbs", ".jar", ".asi")):
                proceed = messagebox.askyesno("Caution: Potential Malicious File",f"{os.path.basename(source)} is an executable file. \nThis could contain potentially malicious code. Make absolutely certain you trust this file, you can use virus scanners like VirusTotal before you use it.\n\nAre you sure you want to install it?")
                if not proceed:
                    self.update_status(f"Skipped {os.path.basename(source)}")
                    return  # Skip the installation for this file
    
            game_folder = self.config.get("Settings", "game_install_folder", fallback="")    																     																			    			    																			   
            if not game_folder or not os.path.isdir(game_folder):
                raise ValueError(f"Invalid game folder path: {game_folder}")
            
            # Use the new mapping function to determine the correct destination
            mapped_destination = self.get_file_destination(os.path.basename(source), mod_folder)
            full_destination = os.path.join(game_folder, mapped_destination if mapped_destination else "")    			    															
            
            print(f"Mapped destination: {full_destination}")
            
            # Check if the destination is inside a zip file
            if ".zip" in full_destination:
                # Handle files intended to go within .zip archives
                zip_path, internal_path = full_destination.split(".zip", 1)
                zip_path += ".zip"
                internal_path = internal_path.lstrip("/")
                self.update_status(f"Updating zip file: {zip_path} at {internal_path}")
                print(f"Updating zip file: {zip_path} at {internal_path}")    														
														
    
                if not os.path.exists(zip_path): # Logic to updating .zip files contents
                    print(f"Warning: Zip file does not exist: {zip_path}")
                    os.makedirs(os.path.dirname(zip_path), exist_ok=True)
                    with zipfile.ZipFile(zip_path, "w") as zf:
                        pass  # Create an empty zip file
                
                # Create a temporary directory to work with the zip file
                with tempfile.TemporaryDirectory() as tmpdirname:
                    # Extract the zip file
                    with zipfile.ZipFile(zip_path, "r") as zip_ref:
                        zip_ref.extractall(tmpdirname)
                    
                    # Copy the new file to the correct location
                    temp_dest = os.path.join(tmpdirname, internal_path)
                    os.makedirs(os.path.dirname(temp_dest), exist_ok=True)
                    shutil.copy2(source, temp_dest)
                    
                    # Create a new zip file with the updated contents
                    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_ref:
                        for root, _, files in os.walk(tmpdirname):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arc_name = os.path.relpath(file_path, tmpdirname)
                                zip_ref.write(file_path, arc_name)
                
                print(f"Updated zip file: {zip_path}")
                self.update_status(f"Updated zip file: {zip_path}")
            else:
                # Place file in regular directory, for files not in zip archives, just copy them directly
                os.makedirs(os.path.dirname(full_destination), exist_ok=True)
                shutil.copy2(source, full_destination)
                print(f"Copied file to: {full_destination}")
                self.update_status(f"Copied file to: {full_destination}")
	
            print(f"Successfully installed: {source} to {full_destination}")
    
        except Exception as e:
            print(f"Error installing file: {source}")
            print(f"Error details: {str(e)}")
            traceback.print_exc()
            error_msg = f"Error installing {source}: {e}"
            self.update_status(f"Last error: {error_msg}")
            self.log_error(error_msg)
    
    def update_status(self, message):
        """Update the status bar message."""
        self.status_var.set(message)
        self.root.update_idletasks()  # Refresh the GUI immediately
    
    def log_error(self, message):
        """Log error messages to a file."""
        with open("mod_manager_log.txt", "a") as log_file:
            log_file.write(message + "\n")

    def install_selected_mods(self):
        # Check if the install button exists and disable it during installation
        if hasattr(self, 'install_button'):
            self.install_button.config(state="disabled")
    
        # Start installation in a background thread
        threading.Thread(target=self._install_selected_mods_thread).start()
    
    def _install_selected_mods_thread(self):
        try:
            self._install_selected_mods_process()
        finally:
            # Re-enable the install button once installation is complete
            if hasattr(self, 'install_button'):
                self.install_button.config(state="normal")
    
    def _install_selected_mods_process(self):
        selected_items = self.mods_table.selection()
        game_folder = self.config.get("Settings", "game_install_folder", fallback="")
    
        if not game_folder or not os.path.isdir(game_folder):
            self.handle_error("Invalid game folder path. Please configure the correct path.")
            return
    
        if not selected_items:
            messagebox.showinfo("No Selection", "Please select one or more mods to install.")
            return
    
        installed_files = []  # Track installed files for post-install verification
    
        for item in selected_items:
            mod_name = self.mods_table.item(item)["values"][0]
            mod_info = next((mod for mod in self.mods if mod["name"] == mod_name), None)
    
            if mod_info:
                mod_folder = mod_info["folder_name"]
                mod_path = os.path.join(MODS_PATH, mod_folder)
    
                # Install each file based on mod.txt paths if available
                if mod_info.get("files"):
                    for file_info in mod_info["files"]:
                        source = os.path.join(mod_path, file_info["source"])
                        destination = file_info.get("destination") or self.get_file_destination(file_info["source"], mod_folder)
                        self.install_mod_file(source, destination, mod_folder)
                        installed_files.append((source, destination))
                else:
                    for root, _, files in os.walk(mod_path):
                        for file in files:
                            if file.lower() not in ["mod.txt", "mod.png"]:
                                source = os.path.join(root, file)
                                destination = self.get_file_destination(file, mod_folder)
                                self.install_mod_file(source, destination, mod_folder)
                                installed_files.append((source, destination))
    
        self.show_installation_summary(installed_files)

    # Detect and handle file conflicts among selected mods.
    def detect_conflicts(self, selected_mods):
        file_destinations = {}
        conflicts = []
    
        # Collect all files and their destinations for selected mods
        for mod in selected_mods:
            mod_info = next((m for m in self.mods if m["name"] == mod), None)
            if mod_info:
                for file_info in mod_info["files"]:
                    destination = self.get_file_destination(file_info["source"], mod_info["folder_name"])
    
                    # Check if another mod has the same destination
                    if destination in file_destinations:
                        conflicts.append((destination, file_destinations[destination], file_info["source"]))
                    else:
                        file_destinations[destination] = file_info["source"]
    
        # Prompt user to resolve conflicts
        if conflicts:
            conflict_message = "Conflicting files detected:\n"
            for dest, existing, new in conflicts:
                conflict_message += f"\nFile '{new}' conflicts with '{existing}' at '{dest}'"
    
            # Let the user decide which version to keep
            if messagebox.askyesno("Conflict Detected", f"{conflict_message}\n\nProceed by keeping the new versions?"):
                # If yes, overwrite with the new files (default behavior)
                self.status_var.set("Resolved conflicts by keeping new files.")
            else:
                # If no, skip installing conflicting files
                self.status_var.set("Resolved conflicts by keeping existing files.")
                for dest, existing, new in conflicts:
                    del file_destinations[dest]  # Remove conflicts to avoid overwriting
    
        return file_destinations  # Return the final set of files to install

    # Show installed files after installation completion in a little dropdown text window after clicking the arrow in the pop-up box
    def show_installation_summary(self, installed_files):
        """Show a summary dialog with a collapsible list of installed files."""
        summary_dialog = tk.Toplevel(self.root)
        summary_dialog.title("Installation Complete")
    
        # Main message
        tk.Label(summary_dialog, text="Installation complete!").pack(padx=10, pady=10)
    
        # Dropdown arrow and toggle button
        dropdown_frame = tk.Frame(summary_dialog)
        dropdown_frame.pack(fill="x", padx=10)
    
        dropdown_label = tk.Label(dropdown_frame, text="More details...", fg="blue", cursor="hand2")
        dropdown_label.pack(side="left")
    
        # Frame for the list of installed files
        files_frame = tk.Frame(summary_dialog)
        files_text = tk.Text(files_frame, wrap="word", height=10, width=60)
        files_text.pack(padx=10, pady=5)
    
        # Populate the file list
        for src, dest in installed_files:
            files_text.insert("end", f"{src} -> {dest}\n")
        files_text.config(state="disabled")  # Make the text box read-only
    
        # Hide files_frame initially
        files_frame.pack_forget()
    
        # Toggle function for showing/hiding installed files
        def toggle_files():
            if files_frame.winfo_ismapped():
                files_frame.pack_forget()
                dropdown_label.config(text="More...")
            else:
                files_frame.pack(fill="both", expand=True, padx=10)
                dropdown_label.config(text="Less...")
    
        # Bind the label click event to toggle the list
        dropdown_label.bind("<Button-1>", lambda e: toggle_files())
    
        # Close button for the dialog
        tk.Button(summary_dialog, text="Close", command=summary_dialog.destroy).pack(pady=5)

# Disabled for now    def get_files_from_archive(self, archive_path):
# Disabled for now        """Returns a list of files within a .zip archive."""
# Disabled for now        with zipfile.ZipFile(archive_path, "r") as zip_ref:
# Disabled for now            return zip_ref.namelist()
# Disabled for now    
# Disabled for now    def replace_file_in_zip(self, zip_path, mod_file_path):
# Disabled for now        """Replaces a file inside a .zip archive without duplicating."""
# Disabled for now        temp_zip_path = zip_path + "_temp"
# Disabled for now    
# Disabled for now        with zipfile.ZipFile(zip_path, 'r') as zip_in, zipfile.ZipFile(temp_zip_path, 'w') as zip_out:
# Disabled for now            # Copy all files from original except the one we want to replace
# Disabled for now            for item in zip_in.infolist():
# Disabled for now                if item.filename != os.path.basename(mod_file_path):
# Disabled for now                    zip_out.writestr(item, zip_in.read(item.filename))
# Disabled for now            # Write the new file into the zip archive
# Disabled for now            zip_out.write(mod_file_path, os.path.basename(mod_file_path))
# Disabled for now    
# Disabled for now        # Replace the original zip file with the modified one
# Disabled for now        os.remove(zip_path)
# Disabled for now        os.rename(temp_zip_path, zip_path)
    
    def copy_mod_file(self, source, destination):
        """Copies a mod file to the game directory, creating directories if needed."""
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.copy2(source, destination)
    
        messagebox.showinfo("Install", "Successfully installed selected mods.")

    def check_backup(self):
        return os.path.exists(BACKUP_PATH) and any(os.scandir(BACKUP_PATH))

    def add_mod(self):
        mod_file = filedialog.askopenfilename(
            title="Select Mod Archive",
            filetypes=[("Zip files", "*.zip")]
        )
        
        if mod_file:
            try:
                with zipfile.ZipFile(mod_file, "r") as zip_ref:
                    zip_ref.extractall(MODS_PATH)
                messagebox.showinfo("Success", "Mod extracted successfully!")
                self.mods = self.load_mods()  # Reload mods
                self.populate_mods_table()    # Refresh table
            except Exception as e:
                messagebox.showerror("Error", f"Failed to extract mod:\n{e}")

    def populate_mods(self):
        print("Populating mod list...")
        self.mod_table.delete(*self.mod_table.get_children())
        for mod in self.mods:
            print(f"Adding mod to list: {mod['name']}")
            file_paths = ", ".join([f"{file['source']} -> {file['destination']}" for file in mod.get("files", [])])
            self.mod_table.insert("", "end", values=(mod["name"], mod.get("description", ""), mod.get("author", ""), file_paths))
        print(f"Mod list populated with {len(self.mods)} mods")
        
        # Update the mod image if available
        if self.mods:
            self.update_mod_image(self.mods[0])

    def update_mod_image(self, mod):
        print(f"Updating mod image for: {mod['name']}")
        if "image_path" in mod and os.path.exists(mod["image_path"]):
            try:
                image = Image.open(mod["image_path"])
                image = image.resize((200, 200), Image.ANTIALIAS)
                photo = ImageTk.PhotoImage(image)
                self.mod_image_label.config(image=photo)
                self.mod_image_label.image = photo
                print(f"Mod image updated: {mod['image_path']}")
            except Exception as e:
                print(f"Error loading mod image: {str(e)}")
                self.mod_image_label.config(image=None, text="No Image Available")
        else:
            print(f"No image available for mod: {mod['name']}")
            self.mod_image_label.config(image=None, text="No Image Available")
    def update_mod_image(self, mod):
        print(f"Updating mod image for: {mod['name']}")
        if "image_path" in mod and os.path.exists(mod["image_path"]):
            try:
                image = Image.open(mod["image_path"])
                image = image.resize((200, 200), Image.ANTIALIAS)
                photo = ImageTk.PhotoImage(image)
                self.mod_image_label.config(image=photo)
                self.mod_image_label.image = photo
                print(f"Mod image updated: {mod['image_path']}")
            except Exception as e:
                print(f"Error loading mod image: {str(e)}")
                self.mod_image_label.config(image=None, text="No Image Available")
        else:
            print(f"No image available for mod: {mod['name']}")
            self.mod_image_label.config(image=None, text="No Image Available")
    def populate_mods_table(self):
        # Clear the table to create a blanking effect
        for item in self.mods_table.get_children():
            self.mods_table.delete(item)
    
        # Set a brief delay to simulate the blanking effect before repopulating
        self.mods_table.after(100, self._populate_mods_table)  # 100 ms delay
    
    def _populate_mods_table(self):
        # Populate the table with mods from the parsed data
        for mod in self.mods:
            # Extract file paths for display in the table
            file_paths = [file["source"] for file in mod["files"]]
            self.mods_table.insert(
                "",
                "end",
                values=(mod["name"], mod["description"], mod["author"], ", ".join(file_paths))
            )

    def check_backup(self):
        """Check if at least one backup exists in the backup directory."""
        # Backup path check with a boolean return value
        return os.path.exists(BACKUP_PATH) and any(os.scandir(BACKUP_PATH))

    def open_config_editor(self):
        """Open a dialog to edit game installation folder path."""
        new_path = filedialog.askdirectory(title="Select Game Installation Folder")
        if new_path:
            self.config["Settings"]["game_install_folder"] = new_path
            with open(CONFIG_PATH, "w") as configfile:
                self.config.write(configfile)
            messagebox.showinfo("Success", "Game folder path updated successfully!")
        else:
            messagebox.showwarning("Warning", "No path selected. Game folder path was not updated.")

    def get_file_destination(self, file_name, mod_folder):
        print(f"Determining destination for file: {file_name}")
        file_extension = os.path.splitext(file_name)[1].lower()
    
        # Special rule for placing config files in the root directory
        if file_name.lower() == "hitmanbloodmoney.ini" or file_extension in [".ini"]:
            print(f"{file_name} will be placed in the main game directory.")
            return file_name
    
        # Special case for saveandcontinue.TEX
        if file_name.lower() == "saveandcontinue.tex":
            return "Scenes/saveandcontinue.zip/Scenes/saveandcontinue.TEX"
        
        # Define mission scene types
        scene_types = ["_albino", "_intro", "_main", "_news", "_premission", "_postmission"]
        missions = ["Hideout"] + [f"M{str(i).zfill(2)}" for i in range(14) if i != 7]
    
        # Match mission-specific files with scene types
        for mission in missions:
            for scene_type in scene_types:
                if file_name.startswith(mission) and scene_type in file_name:
                    return f"Scenes/{mission}/{mission}{scene_type}.zip/Scenes/{mission}/{file_name}"
    
        # Handle general file types that go into mission folders
        general_types = [".anm", ".buf", ".gms", ".loc", ".mat", ".oct", ".prm", ".prp", ".rmc", ".rmi", ".sgd", ".sgp", ".snd", ".sup", ".tex", ".zgf"]
        if file_extension in general_types:
            # Assume it goes into the main mission folder matching the mod folder name
            for mission in missions:
                if mission.lower() in mod_folder.lower():
                    return f"Scenes/{mission}/{mission}_main.zip/Scenes/{mission}/{file_name}"
    
        # Special cases for HitmanBloodMoney.zip and saveandcontinue.zip (single location rules)
        if "hitmanbloodmoney" in file_name.lower():
            return f"Scenes/HitmanBloodMoney.zip/Scenes/{file_name}"
        if "saveandcontinue" in file_name.lower():
            return f"Scenes/saveandcontinue.zip/Scenes/{file_name}"
    
        # Default case: place in the main game directory if no other rule matches
        print(f"No specific rule for {file_name}, placing in main game directory")
        return file_name

    def delete_mod(self):
        selected_item = self.mods_table.selection()
        if selected_item:
            mod_name = self.mods_table.item(selected_item[0])["values"][0]
            confirm = messagebox.askyesno("Delete Mod", f"Are you sure you want to delete '{mod_name}'?")
            if confirm:
                for mod in self.mods:
                    if mod["name"] == mod_name:
                        mod_path = mod["path"]
                        try:
                            send2trash(mod_path)
                            messagebox.showinfo("Deleted", f"'{mod_name}' has been deleted.")
                            self.mods.remove(mod)
                            self.populate_mods_table()
                        except Exception as e:
                            messagebox.showerror("Error", f"Failed to delete '{mod_name}': {e}")
                        break

    def explore_mod_contents(self):
        selected_items = self.mods_table.selection()
    
        if not selected_items:
            messagebox.showinfo("No Selection", "Please select one or more mods to explore.")
            return
    
        # Warn if multiple folders are selected
        if len(selected_items) > 1:
            proceed = messagebox.askyesno("Multiple Mods Selected", "Are you sure you want to open multiple mod folders?")
            if not proceed:
                return
    
        # Open each selected mod's folder
        for item in selected_items:
            mod_name = self.mods_table.item(item)["values"][0]
            mod_info = next((mod for mod in self.mods if mod["name"] == mod_name), None)
    
            if mod_info:
                mod_path = os.path.join(MODS_PATH, mod_info["folder_name"])
                print(f"Opening folder: {mod_path}")
    
                if os.path.exists(mod_path):
                    if os.name == 'nt':  # For Windows
                        subprocess.Popen(f'explorer "{mod_path}"')
                    elif os.name == 'posix':  # For macOS/Linux
                        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", mod_path])
                else:
                    print(f"Error: Mod folder does not exist at {mod_path}")
                    messagebox.showerror("Error", f"Mod folder not found: {mod_path}")

# Run the application
if __name__ == "__main__":
    print("Main block executed.")
    root = tk.Tk()
    app = ModManagerApp(root)
    root.mainloop()