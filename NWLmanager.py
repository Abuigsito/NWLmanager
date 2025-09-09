import json
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, simpledialog
import requests
import base64
from urllib.parse import urlparse
import os
import re
import sys
import tkinter.font as tkfont

# DPI Awareness para una mejor renderización en Windows
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except ImportError:
    pass  # Para sistemas operativos que no son Windows
except Exception:
    pass  # Para versiones antiguas de Windows

class GitHubJSONEditor:
    def __init__(self, root):
        self.root = root
        
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(3, weight=1) # Permitir que el frame del JSON también se expanda
        self.root.columnconfigure(0, weight=1)

        # Fuentes estándar y limpias
        self.font_normal = tkfont.Font(family="Segoe UI", size=10)
        self.font_mono = tkfont.Font(family="Consolas", size=10)

        # Valores de configuración por defecto
        self.repo_url = "https://github.com/Abuigsito/nowavelist"
        self.folder_path = "data"
        self.current_lang = "es"
        self.github_token = ""
        self.load_config()

        self.current_file_content = None
        self.selected_record_id = None
        self.current_file_sha = None

        self.setup_translations()
        # self.current_lang ya está establecido por load_config o por defecto

        self.create_widgets()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def create_widgets(self):
        self.root.title(self.translate("title"))
        # Frame para configuración de GitHub
        github_frame = ttk.LabelFrame(self.root, text=self.translate("github_config"), padding="10")
        github_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        github_frame.columnconfigure(1, weight=1)

        ttk.Label(github_frame, text=self.translate("repo_url"), font=self.font_normal).grid(row=0, column=0, sticky="w", pady=5)
        self.repo_url_entry = ttk.Entry(github_frame, width=50, font=self.font_normal)
        self.repo_url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.repo_url_entry.insert(0, self.repo_url)
        self.repo_url_entry.config(state="disabled")  # Deshabilitar edición
        
        ttk.Label(github_frame, text=self.translate("json_folder"), font=self.font_normal).grid(row=1, column=0, sticky="w", pady=5)
        self.folder_entry = ttk.Entry(github_frame, width=50, font=self.font_normal)
        self.folder_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.folder_entry.insert(0, self.folder_path)
        self.folder_entry.config(state="disabled")  # Deshabilitar edición
        
        # Frame para botones de GitHub
        github_buttons_frame = ttk.Frame(github_frame)
        github_buttons_frame.grid(row=1, column=2, sticky="w", padx=5)

        ttk.Button(github_buttons_frame, text=self.translate("settings"), command=self.open_settings_window, style="Custom.TButton").pack(side="left")
        ttk.Button(github_buttons_frame, text=self.translate("load_files"), command=self.load_github_files, 
                   style="Custom.TButton").pack(side="left", padx=5)

        ttk.Label(github_frame, text=self.translate("github_token"), font=self.font_normal).grid(row=2, column=0, sticky="w", pady=5)
        self.token_entry = ttk.Entry(github_frame, width=50, show="*", font=self.font_normal)
        self.token_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.token_entry.insert(0, self.github_token)
        self.token_entry.config(state="disabled")

        # Frame para archivos JSON
        files_frame = ttk.LabelFrame(self.root, text=self.translate("json_files"), padding="10")
        files_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        files_frame.rowconfigure(1, weight=1)
        files_frame.columnconfigure(0, weight=1)

        # Barra de búsqueda
        search_frame = ttk.Frame(files_frame)
        search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        search_frame.columnconfigure(1, weight=1)
        ttk.Label(search_frame, text=self.translate("search"), font=self.font_normal).grid(row=0, column=0, sticky="w")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.update_search)
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30, font=self.font_normal)
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=5)

        self.files_listbox = tk.Listbox(files_frame, height=8, font=self.font_normal)
        self.files_listbox.grid(row=1, column=0, sticky="nsew")
        self.files_listbox.bind('<<ListboxSelect>>', self.on_file_select)

        scrollbar = ttk.Scrollbar(files_frame, orient="vertical", command=self.files_listbox.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.files_listbox.config(yscrollcommand=scrollbar.set)

        if hasattr(self, 'display_files') and self.display_files:
            self.update_files_listbox()

        # Frame para edición
        edit_frame = ttk.LabelFrame(self.root, text=self.translate("edit_record"), padding="10")
        edit_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        edit_frame.columnconfigure(1, weight=1)

        ttk.Label(edit_frame, text=self.translate("user"), font=self.font_normal).grid(row=0, column=0, sticky="w", pady=5)
        self.user_entry = ttk.Entry(edit_frame, width=30, font=self.font_normal)
        self.user_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(edit_frame, text=self.translate("link"), font=self.font_normal).grid(row=1, column=0, sticky="w", pady=5)
        self.link_entry = ttk.Entry(edit_frame, width=30, font=self.font_normal)
        self.link_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(edit_frame, text=self.translate("percent"), font=self.font_normal).grid(row=2, column=0, sticky="w", pady=5)
        self.percent_entry = ttk.Entry(edit_frame, width=30, font=self.font_normal)
        self.percent_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(edit_frame, text=self.translate("hz"), font=self.font_normal).grid(row=3, column=0, sticky="w", pady=5)
        self.hz_entry = ttk.Entry(edit_frame, width=30, font=self.font_normal)
        self.hz_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(edit_frame, text=self.translate("mobile"), font=self.font_normal).grid(row=4, column=0, sticky="w", pady=5)
        self.mobile_var = tk.BooleanVar()
        ttk.Checkbutton(edit_frame, text="", variable=self.mobile_var).grid(row=4, column=1, sticky="w", padx=5, pady=5)

        # Frame para botones de edición de records
        record_buttons_frame = ttk.Frame(edit_frame)
        record_buttons_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        self.update_list_button = ttk.Button(record_buttons_frame, text=self.translate("update_list"), command=self.open_list_updater, style="Custom.TButton")
        self.update_list_button.pack(side="left")
        ttk.Button(record_buttons_frame, text=self.translate("add_level"), command=self.open_add_level_window, 
                   style="Custom.TButton").pack(side="left", padx=5)
        self.edit_level_button = ttk.Button(record_buttons_frame, text=self.translate("edit_level"), command=self.open_edit_level_window, style="Custom.TButton")
        self.edit_level_button.pack(side="left")
                   
        ttk.Button(record_buttons_frame, text=self.translate("delete_record"), command=self.delete_record, 
                   style="Custom.TButton").pack(side="right", padx=(5, 0))
        ttk.Button(record_buttons_frame, text=self.translate("update_record"), command=self.update_record, 
                   style="Custom.TButton").pack(side="right", padx=5)
        ttk.Button(record_buttons_frame, text=self.translate("add_record"), command=self.add_record, 
                   style="Custom.TButton").pack(side="right")

        # Frame para la tabla de records
        records_frame = ttk.LabelFrame(self.root, text=self.translate("file_records"), padding="10")
        records_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=5)
        records_frame.rowconfigure(0, weight=1)
        records_frame.columnconfigure(0, weight=1)

        columns = ("user", "link", "percent", "hz", "mobile")
        self.records_tree = ttk.Treeview(records_frame, columns=columns, show="headings", height=10)
        
        self.records_tree.heading("user", text=self.translate("user"))
        self.records_tree.heading("link", text=self.translate("link"))
        self.records_tree.heading("percent", text=self.translate("percent"))
        self.records_tree.heading("hz", text=self.translate("hz"))
        self.records_tree.heading("mobile", text=self.translate("mobile"))

        self.records_tree.column("user", width=150)
        self.records_tree.column("link", width=300)
        self.records_tree.column("percent", width=80, anchor="center")
        self.records_tree.column("hz", width=80, anchor="center")
        self.records_tree.column("mobile", width=60, anchor="center")

        self.records_tree.grid(row=0, column=0, sticky="nsew")
        self.records_tree.bind('<<TreeviewSelect>>', self.on_record_select)

        tree_scrollbar = ttk.Scrollbar(records_frame, orient="vertical", command=self.records_tree.yview)
        tree_scrollbar.grid(row=0, column=1, sticky="ns")
        self.records_tree.config(yscrollcommand=tree_scrollbar.set)

        # Frame para botones de acción
        action_frame = ttk.Frame(self.root, padding="10")
        action_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=5)
        action_frame.columnconfigure(0, weight=1)

        self.text_editor_button = ttk.Button(action_frame, text=self.translate("text_editor"), command=self.open_text_editor, style="Custom.TButton")
        self.text_editor_button.pack(side="left", padx=5)
        self.save_changes_button = ttk.Button(action_frame, text=self.translate("save_changes"), command=self.save_changes, style="Custom.TButton")
        self.save_changes_button.pack(side="right", padx=5)

        # Configurar estilo de botones personalizados
        style = ttk.Style()
        style.configure("Custom.TButton", font=self.font_normal)

        if self.current_file_content:
            self.populate_records_treeview()

        self.update_contextual_button_states()

    def update_contextual_button_states(self):
        """Habilita o deshabilita botones según el estado de la aplicación."""
        # Estado para botones que dependen de un archivo seleccionado
        file_selected_state = "normal" if self.current_file_content is not None else "disabled"
        
        # El botón de actualizar lista solo necesita que la lista de archivos de GitHub esté cargada.
        list_loaded = hasattr(self, 'display_files') and self.display_files
        update_list_state = "normal" if list_loaded else "disabled"

        self.update_list_button.config(state=update_list_state)
        self.edit_level_button.config(state=file_selected_state)
        self.text_editor_button.config(state=file_selected_state)
        self.save_changes_button.config(state=file_selected_state)

    def setup_translations(self):
        self.translations = {
            "es": {
                "title": "No Wave List Manager", "github_config": "Configuración de GitHub", "repo_url": "URL del repositorio:", "github_token": "Token GitHub (config.json):",
                "json_folder": "Carpeta de JSONs:", "settings": "Configuración", "load_files": "Cargar Archivos", "json_files": "Archivos JSON", "search": "Buscar:",
                "edit_record": "Editar Record", "user": "Usuario", "link": "Link", "percent": "Porcentaje", "hz": "Hz",
                "mobile": "Mobile", "update_list": "Actualizar Lista", "add_level": "Añadir Nivel", "edit_level": "Editar Nivel",
                "delete_record": "Eliminar Record", "update_record": "Actualizar Record", "add_record": "Agregar Record",
                "file_records": "Records del Archivo", "text_editor": "Editor de Texto", "save_changes": "Guardar Cambios",
                "language": "Idioma", "settings_saved": "Configuración Guardada", "settings_updated": "La configuración ha sido actualizada.",
                "save": "Guardar", "cancel": "Cancelar", "error": "Error", "warning": "Advertencia", "success": "Éxito",
                "confirm_deletion": "Confirmar Eliminación", "yes": "Sí", "no": "No",
                "error_url_folder_empty": "La URL del repositorio y la carpeta no pueden estar vacíos.",
                "error_invalid_github_url": "URL de GitHub inválida",
                "success_files_found": "Se encontraron {count} archivos JSON",
                "error_loading_files": "No se pudieron cargar los archivos: {error}",
                "error_unexpected": "Error inesperado: {error}",
                "error_loading_file": "No se pudo cargar el archivo: {error}",
                "error_processing_file": "Error al procesar el archivo: {error}",
                "warn_select_json": "Primero selecciona un archivo JSON",
                "warn_user_link_mandatory": "Usuario y Link son campos obligatorios",
                "warn_percent_integer": "El campo 'Porcentaje' debe ser un número entero.",
                "success_record_added": "Record agregado correctamente",
                "warn_select_record_update": "Selecciona un record para actualizar",
                "warn_user_link_empty": "Usuario y Link no pueden estar vacíos",
                "success_record_updated": "Record actualizado correctamente",
                "warn_select_record_delete": "Selecciona un record para eliminar",
                "confirm_delete_record": "¿Estás seguro de que quieres eliminar este record?",
                "success_record_deleted": "Record eliminado correctamente",
                "error_deleting_record": "No se pudo eliminar el record seleccionado.",
                "accept": "Aceptar",
                "edit_level_title": "Editar Nivel: {filename}",
                "level_id": "ID", "level_name": "Nombre", "level_author": "Autor", "level_verifier": "Verificador",
                "level_creators": "Creadores (separados por coma)", "level_verification_link": "Link de Verificación",
                "level_percent_qualify": "Porcentaje para Calificar",
                "commit_update_metadata": "Actualizar metadatos de {filename}",
                "success_metadata_updated": "Metadatos del nivel actualizados correctamente.",
                "error_id_percent_integer": "Los campos 'ID' y 'Porcentaje para Calificar' deben ser números enteros.",
                "error_saving_changes": "No se pudieron guardar los cambios: {error}",
                "confirm_delete_level": "¿Estás seguro de que quieres eliminar el archivo '{filename}' de GitHub?\n\nEsta acción es irreversible.",
                "commit_delete_level": "Eliminar nivel: {filename}",
                "success_file_deleted": "Archivo '{filename}' eliminado de GitHub.",
                "error_deleting_file": "No se pudo eliminar el archivo: {error}",
                "delete_level": "Eliminar Nivel",
                "add_new_level": "Añadir Nuevo Nivel",
                "warn_config_repo_folder": "Primero configura el repositorio y la carpeta en 'Configuraciones'.",
                "import_from_aredl": "Importar desde AREDL",
                "aredl_import_prompt": "Introduce el ID del nivel de AREDL:",
                "invalid_input": "Entrada inválida", "numeric_id_required": "Por favor, introduce un ID numérico.",
                "success_aredl_import": "Datos del nivel importados correctamente desde AREDL.",
                "api_error": "Error de API", "api_error_details": "Error al contactar la API de AREDL (código: {code}).\nVerifica que el ID '{level_id}' sea correcto.",
                "network_error": "Error de Red", "network_error_details": "No se pudo conectar con la API de AREDL: {e}",
                "all_fields_mandatory": "Todos los campos son obligatorios.",
                "invalid_level_name_filename": "El nombre del nivel es inválido para crear un nombre de archivo.",
                "file_already_exists": "Un archivo con un nombre similar a '{filename}' ya existe.",
                "token_needed_to_create": "Se necesita un token de GitHub en token.txt para crear un archivo.",
                "commit_add_level": "Añadir nuevo nivel: {name}",
                "success_level_added": "Nivel '{name}' añadido como '{filename}' en GitHub.",
                "error_creating_file": "No se pudo crear el archivo en GitHub: {error}",
                "select_order_file": "Seleccionar Archivo de Orden",
                "warn_load_files_first": "Primero carga los archivos desde GitHub con el botón 'Cargar Archivos'.",
                "select_order_file_label": "Selecciona el archivo que contiene el orden:",
                "warn_select_file": "Debes seleccionar un archivo.", "select": "Seleccionar",
                "format_error": "Error de Formato", "format_error_details": "El archivo '{filename}' no contiene una lista de texto (strings).",
                "error_loading_order_file": "No se pudo cargar el archivo de orden: {str(e)}",
                "file_error": "Error de Archivo", "file_error_details": "El archivo '{filename}' no es un JSON válido.",
                "error_processing_order_file": "Error al procesar el archivo de orden: {str(e)}",
                "reorder_list": "Reordenar Lista", "add": "Añadir", "delete": "Eliminar", "up": "Subir", "down": "Bajar",
                "save_apply": "Guardar y Aplicar", "success_list_reordered": "La lista de records ha sido reordenada.",
                "text_editor_title": "Editor de Texto: {filename}", "save_close": "Guardar y Cerrar",
                "success_content_updated_memory": "Contenido actualizado en memoria.\nRecuerda usar 'Guardar Cambios' para subirlo a GitHub.",
                "json_error": "Error de JSON", "json_error_details": "El texto no es un JSON válido.\n\n{e}",
                "token_needed_to_save": "Se necesita un token de GitHub en token.txt para guardar cambios",
                "commit_update_records": "Actualización de records en {filename}",
                "success_changes_saved_github": "Cambios guardados correctamente en GitHub"
            },
            "en": {
                "title": "No Wave List Manager", "github_config": "GitHub Configuration", "repo_url": "Repository URL:",
                "json_folder": "JSONs Folder:", "settings": "Settings", "load_files": "Load Files", "github_token": "GitHub Token (config.json):", "json_files": "JSON Files", "search": "Search:",
                "edit_record": "Edit Record", "user": "User", "link": "Link", "percent": "Percent", "hz": "Hz",
                "mobile": "Mobile", "update_list": "Update List", "add_level": "Add Level", "edit_level": "Edit Level",
                "delete_record": "Delete Record", "update_record": "Update Record", "add_record": "Add Record",
                "file_records": "File Records", "text_editor": "Text Editor", "save_changes": "Save Changes",
                "language": "Language", "settings_saved": "Settings Saved", "settings_updated": "The configuration has been updated.",
                "save": "Save", "cancel": "Cancel", "error": "Error", "warning": "Warning", "success": "Success",
                "confirm_deletion": "Confirm Deletion", "yes": "Yes", "no": "No",
                "error_url_folder_empty": "Repository URL and folder cannot be empty.",
                "error_invalid_github_url": "Invalid GitHub URL",
                "success_files_found": "Found {count} JSON files",
                "error_loading_files": "Could not load files: {error}",
                "error_unexpected": "Unexpected error: {error}",
                "error_loading_file": "Could not load file: {error}",
                "error_processing_file": "Error processing file: {error}",
                "warn_select_json": "First, select a JSON file",
                "warn_user_link_mandatory": "User and Link are mandatory fields",
                "warn_percent_integer": "'Percent' field must be an integer.",
                "success_record_added": "Record added successfully",
                "warn_select_record_update": "Select a record to update",
                "warn_user_link_empty": "User and Link cannot be empty",
                "success_record_updated": "Record updated successfully",
                "warn_select_record_delete": "Select a record to delete",
                "confirm_delete_record": "Are you sure you want to delete this record?",
                "success_record_deleted": "Record deleted successfully",
                "error_deleting_record": "Could not delete the selected record.",
                "accept": "Accept",
                "edit_level_title": "Edit Level: {filename}",
                "level_id": "ID", "level_name": "Name", "level_author": "Author", "level_verifier": "Verifier",
                "level_creators": "Creators (comma-separated)", "level_verification_link": "Verification Link",
                "level_percent_qualify": "Percent to Qualify",
                "commit_update_metadata": "Update metadata for {filename}",
                "success_metadata_updated": "Level metadata updated successfully.",
                "error_id_percent_integer": "'ID' and 'Percent to Qualify' fields must be integers.",
                "error_saving_changes": "Could not save changes: {error}",
                "confirm_delete_level": "Are you sure you want to delete the file '{filename}' from GitHub?\n\nThis action is irreversible.",
                "commit_delete_level": "Delete level: {filename}",
                "success_file_deleted": "File '{filename}' deleted from GitHub.",
                "error_deleting_file": "Could not delete file: {error}",
                "delete_level": "Delete Level",
                "add_new_level": "Add New Level",
                "warn_config_repo_folder": "First, configure the repository and folder in 'Settings'.",
                "import_from_aredl": "Import from AREDL",
                "aredl_import_prompt": "Enter the AREDL level ID:",
                "invalid_input": "Invalid Input", "numeric_id_required": "Please enter a numeric ID.",
                "success_aredl_import": "Level data imported successfully from AREDL.",
                "api_error": "API Error", "api_error_details": "Error contacting AREDL API (code: {code}).\nVerify that the ID '{level_id}' is correct.",
                "network_error": "Network Error", "network_error_details": "Could not connect to AREDL API: {e}",
                "all_fields_mandatory": "All fields are mandatory.",
                "invalid_level_name_filename": "The level name is invalid for creating a filename.",
                "file_already_exists": "A file with a name similar to '{filename}' already exists.",
                "token_needed_to_create": "A GitHub token in token.txt is required to create a file.",
                "commit_add_level": "Add new level: {name}",
                "success_level_added": "Level '{name}' added as '{filename}' on GitHub.",
                "error_creating_file": "Could not create the file on GitHub: {error}",
                "select_order_file": "Select Order File",
                "warn_load_files_first": "First, load files from GitHub using the 'Load Files' button.",
                "select_order_file_label": "Select the file containing the order:",
                "warn_select_file": "You must select a file.", "select": "Select",
                "format_error": "Format Error", "format_error_details": "The file '{filename}' does not contain a list of strings.",
                "error_loading_order_file": "Could not load the order file: {str(e)}",
                "file_error": "File Error", "file_error_details": "The file '{filename}' is not a valid JSON.",
                "error_processing_order_file": "Error processing the order file: {str(e)}",
                "reorder_list": "Reorder List", "add": "Add", "delete": "Delete", "up": "Up", "down": "Down",
                "save_apply": "Save and Apply", "success_list_reordered": "The records list has been reordered.",
                "text_editor_title": "Text Editor: {filename}", "save_close": "Save and Close",
                "success_content_updated_memory": "Content updated in memory.\nRemember to use 'Save Changes' to upload it to GitHub.",
                "json_error": "JSON Error", "json_error_details": "The text is not a valid JSON.\n\n{e}",
                "token_needed_to_save": "A GitHub token in token.txt is needed to save changes",
                "commit_update_records": "Update records in {filename}",
                "success_changes_saved_github": "Changes saved successfully to GitHub"
            }
        }

    def translate(self, key):
        return self.translations.get(self.current_lang, self.translations["en"]).get(key, key)

    def get_config_path(self):
        """Devuelve la ruta al archivo de configuración."""
        if getattr(sys, 'frozen', False):
            # Si la aplicación está "congelada" (ejecutable), la base es el directorio del .exe
            base_path = os.path.dirname(sys.executable)
        else:
            # Si se está ejecutando como un script normal, la base es el directorio del script
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, "config.json")

    def load_config(self):
        """Carga la configuración desde config.json."""
        try:
            config_path = self.get_config_path()
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.repo_url = config.get("repo_url", self.repo_url)
                    self.folder_path = config.get("folder_path", self.folder_path)
                    self.current_lang = config.get("language", self.current_lang)
                    self.github_token = config.get("github_token", "")
        except (IOError, json.JSONDecodeError):
            # Usar valores por defecto si el archivo no existe o está corrupto
            pass

    def save_config(self):
        """Guarda la configuración actual en config.json, preservando claves existentes como el token."""
        config_path = self.get_config_path()
        config = {}
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
        except (IOError, json.JSONDecodeError):
            # Si el archivo está corrupto o es ilegible, empezamos de cero
            # pero no perdemos la configuración actual de la app.
            config = {}

        # Actualizar el diccionario con los valores actuales de la app
        config['repo_url'] = self.repo_url
        config['folder_path'] = self.folder_path
        config['language'] = self.current_lang

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except IOError:
            # No se pudo guardar la configuración, pero no interrumpimos el cierre.
            pass

    def on_closing(self):
        """Maneja el evento de cierre de la ventana."""
        self.save_config()
        self.root.destroy()
        
    def parse_github_url(self, url):
        """Extrae el propietario y el nombre del repo de una URL de GitHub."""
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        
        if len(path_parts) >= 2:
            owner = path_parts[0]
            repo = path_parts[1]
            return owner, repo
        return None, None
    
    def open_settings_window(self):
        """Abre una ventana emergente para editar la configuración."""
        settings_win = tk.Toplevel(self.root)
        settings_win.title(self.translate("settings"))
        settings_win.transient(self.root)
        settings_win.grab_set()
        settings_win.resizable(False, False)

        main_frame = ttk.Frame(settings_win, padding="10")
        main_frame.pack(expand=True, fill="both")

        ttk.Label(main_frame, text=self.translate("repo_url"), font=self.font_normal).grid(row=0, column=0, sticky="w", pady=5)
        url_entry = ttk.Entry(main_frame, width=60, font=self.font_normal)
        url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        url_entry.insert(0, self.repo_url_entry.get())

        ttk.Label(main_frame, text=self.translate("json_folder"), font=self.font_normal).grid(row=1, column=0, sticky="w", pady=5)
        folder_entry = ttk.Entry(main_frame, width=60, font=self.font_normal)
        folder_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        folder_entry.insert(0, self.folder_entry.get())

        ttk.Label(main_frame, text=self.translate("language") + ":", font=self.font_normal).grid(row=2, column=0, sticky="w", pady=5)
        lang_combo = ttk.Combobox(main_frame, values=["Español", "English"], state="readonly", font=self.font_normal)
        lang_combo.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        lang_combo.set("Español" if self.current_lang == "es" else "English")

        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=3, column=1, sticky="e", pady=(10, 0))

        def save_and_close():
            self.repo_url = url_entry.get()
            self.folder_path = folder_entry.get()

            # Actualizar la UI principal (aunque estén deshabilitados, es buena práctica)
            self.repo_url_entry.config(state="normal"); self.repo_url_entry.delete(0, tk.END); self.repo_url_entry.insert(0, self.repo_url); self.repo_url_entry.config(state="disabled")
            self.folder_entry.config(state="normal"); self.folder_entry.delete(0, tk.END); self.folder_entry.insert(0, self.folder_path); self.folder_entry.config(state="disabled")

            new_lang_str = lang_combo.get()
            new_lang = "es" if new_lang_str == "Español" else "en"
            
            lang_changed = self.current_lang != new_lang
            if lang_changed:
                self.current_lang = new_lang

            messagebox.showinfo(self.translate("settings_saved"), self.translate("settings_updated"), parent=settings_win)
            settings_win.destroy()

            if lang_changed:
                self.update_ui_language()


        ttk.Button(buttons_frame, text=self.translate("save"), command=save_and_close, style="Custom.TButton").pack(side="right")
        ttk.Button(buttons_frame, text=self.translate("cancel"), command=settings_win.destroy, style="Custom.TButton").pack(side="right", padx=5)
        main_frame.columnconfigure(1, weight=1)

        # Centrar la ventana emergente sobre la principal
        settings_win.update_idletasks()
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()
        win_width = settings_win.winfo_width()
        win_height = settings_win.winfo_height()
        pos_x = root_x + (root_width // 2) - (win_width // 2)
        pos_y = root_y + (root_height // 2) - (win_height // 2)
        settings_win.geometry(f"+{pos_x}+{pos_y}")
        settings_win.focus_set()

    def update_ui_language(self):
        """Destruye y recrea todos los widgets para aplicar el nuevo idioma."""
        for widget in self.root.winfo_children():
            widget.destroy()
        self.create_widgets()
        self.load_github_files() # Recargar para que todo esté consistente

        
    def load_github_files(self):
        """Carga los archivos JSON del repositorio de GitHub y muestra el nombre del archivo."""
        self.repo_url = self.repo_url_entry.get()
        self.folder_path = self.folder_entry.get()
        token = self.github_token

        if not self.repo_url or not self.folder_path:
            messagebox.showerror(self.translate("error"), self.translate("error_url_folder_empty"))
            return

        owner, repo = self.parse_github_url(self.repo_url)
        if not owner or not repo:
            messagebox.showerror(self.translate("error"), self.translate("error_invalid_github_url"))
            return

        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{self.folder_path}"

        headers = {}
        if token:
            headers['Authorization'] = f'token {token}'

        try:
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()

            files = response.json()
            json_files = [file['name'] for file in files if file['name'].endswith('.json')]

            # Mostrar solo los nombres de archivo
            self.display_files = [{"name": file_name, "file_name": file_name} for file_name in json_files]
            self.update_files_listbox()

            # Limpiar selección actual y actualizar estado de botones
            self.current_file_content = None
            self.current_file_name = None
            self.current_file_sha = None
            self.populate_records_treeview()
            self.update_contextual_button_states()

            messagebox.showinfo(self.translate("success"), self.translate("success_files_found").format(count=len(self.display_files)))

        except requests.exceptions.RequestException as e:
            messagebox.showerror(self.translate("error"), self.translate("error_loading_files").format(error=str(e)))
        except Exception as e:
            messagebox.showerror(self.translate("error"), self.translate("error_unexpected").format(error=str(e)))

    def update_files_listbox(self, filter_text=""):
        """Actualiza la lista de archivos mostrados en el listbox, usando filtro si aplica."""
        self.files_listbox.delete(0, tk.END)
        for item in self.display_files:
            if filter_text.lower() in item["name"].lower():
                self.files_listbox.insert(tk.END, item["name"])

    def update_search(self, *args):
        """Filtra la lista de archivos según la búsqueda."""
        filter_text = self.search_var.get()
        self.update_files_listbox(filter_text)

    def on_file_select(self, event):
        """Cuando se selecciona un archivo de la lista"""
        selection = self.files_listbox.curselection()
        if not selection:
            return
        selected_name = self.files_listbox.get(selection[0])
        # Buscar el file_name correspondiente
        for item in self.display_files:
            if item["name"] == selected_name:
                self.load_file_content(item["file_name"])
                break
    
    def load_file_content(self, file_name):
        """Carga el contenido del archivo seleccionado"""
        owner, repo = self.parse_github_url(self.repo_url)
        token = self.github_token
        
        file_path = f"{self.folder_path}/{file_name}"
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
        
        headers = {}
        if token:
            headers['Authorization'] = f'token {token}'
        
        try:
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            
            file_data = response.json()
            content = base64.b64decode(file_data['content']).decode('utf-8')
            
            self.current_file_content = json.loads(content)
            self.current_file_name = file_name
            self.current_file_sha = file_data['sha']
            
            self.populate_records_treeview()
            self.update_contextual_button_states()
            
        except requests.exceptions.RequestException as e:
            messagebox.showerror(self.translate("error"), self.translate("error_loading_file").format(error=str(e)))
        except Exception as e:
            messagebox.showerror(self.translate("error"), self.translate("error_processing_file").format(error=str(e)))
    
    def on_record_select(self, event):
        """Cuando se selecciona un record de la tabla"""
        selection = self.records_tree.selection()
        if not selection:
            self.selected_record_id = None
            return
        
        self.selected_record_id = selection[0]
        record_values = self.records_tree.item(self.selected_record_id, 'values')

        self.user_entry.delete(0, tk.END)
        self.user_entry.insert(0, record_values[0])

        self.link_entry.delete(0, tk.END)
        self.link_entry.insert(0, record_values[1])

        self.percent_entry.delete(0, tk.END)
        self.percent_entry.insert(0, record_values[2])

        self.hz_entry.delete(0, tk.END)
        self.hz_entry.insert(0, record_values[3])

        self.mobile_var.set(record_values[4] == self.translate("yes"))

    def populate_records_treeview(self):
        """Rellena la tabla con los records del archivo actual"""
        # Limpiar tabla
        for i in self.records_tree.get_children():
            self.records_tree.delete(i)

        # Limpiar campos de entrada y selección
        self.user_entry.delete(0, tk.END)
        self.link_entry.delete(0, tk.END)
        self.percent_entry.delete(0, tk.END)
        self.percent_entry.insert(0, "100")
        self.hz_entry.delete(0, tk.END)
        self.hz_entry.insert(0, " ")
        self.mobile_var.set(False)
        self.selected_record_id = None

        if self.current_file_content and "records" in self.current_file_content:
            for i, record in enumerate(self.current_file_content["records"]):
                mobile_status = self.translate("yes") if record.get("mobile") is True else self.translate("no")
                values = (record.get("user", ""), record.get("link", ""), record.get("percent", ""), record.get("hz", ""), mobile_status)
                self.records_tree.insert("", tk.END, iid=str(i), values=values)
    
    def add_record(self):
        """Agrega un nuevo record al JSON"""
        if self.current_file_content is None:
            messagebox.showwarning(self.translate("warning"), self.translate("warn_select_json"))
            return

        user = self.user_entry.get().strip()
        link = self.link_entry.get().strip()
        percent_str = self.percent_entry.get().strip()
        hz = self.hz_entry.get().strip()

        if not user or not link:
            messagebox.showwarning(self.translate("warning"), self.translate("warn_user_link_mandatory"))
            return

        try:
            percent = int(percent_str)
        except ValueError:
            messagebox.showwarning(self.translate("warning"), self.translate("warn_percent_integer"))
            return

        # Crear nuevo record
        new_record = {
            "user": user,
            "link": link,
            "percent": percent,
            "hz": hz
        }
        if self.mobile_var.get():
            new_record["mobile"] = True

        # Asegurarse de que existe el array de records
        if "records" not in self.current_file_content:
            self.current_file_content["records"] = []

        # Agregar el nuevo record
        self.current_file_content["records"].append(new_record)

        # Actualizar la vista (esto también limpia y resetea los campos)
        self.populate_records_treeview()

        messagebox.showinfo(self.translate("success"), self.translate("success_record_added"))

    def update_record(self):
        """Actualiza un record existente"""
        if self.selected_record_id is None:
            messagebox.showwarning(self.translate("warning"), self.translate("warn_select_record_update"))
            return

        user = self.user_entry.get().strip()
        link = self.link_entry.get().strip()
        percent_str = self.percent_entry.get().strip()
        hz = self.hz_entry.get().strip()

        if not user or not link:
            messagebox.showwarning(self.translate("warning"), self.translate("warn_user_link_empty"))
            return

        try:
            percent = int(percent_str)
        except ValueError:
            messagebox.showwarning(self.translate("warning"), self.translate("warn_percent_integer"))
            return

        record_index = int(self.selected_record_id)
        record = self.current_file_content["records"][record_index]
        
        record["user"] = user
        record["link"] = link
        record["percent"] = percent
        record["hz"] = hz

        if self.mobile_var.get():
            record["mobile"] = True
        elif "mobile" in record:
            del record["mobile"]

        self.populate_records_treeview()
        messagebox.showinfo(self.translate("success"), self.translate("success_record_updated"))

    def delete_record(self):
        """Elimina el record seleccionado"""
        if self.selected_record_id is None:
            messagebox.showwarning(self.translate("warning"), self.translate("warn_select_record_delete"))
            return

        if not messagebox.askyesno(self.translate("confirm_deletion"), self.translate("confirm_delete_record")):
            return

        try:
            record_index = int(self.selected_record_id)
            del self.current_file_content["records"][record_index]
            
            self.populate_records_treeview()
            messagebox.showinfo(self.translate("success"), self.translate("success_record_deleted"))
        except (ValueError, IndexError):
            messagebox.showerror(self.translate("error"), self.translate("error_deleting_record"))

    def _custom_ask_string(self, title, prompt, parent):
        """Un reemplazo personalizado para simpledialog.askstring que usa botones ttk estilizados."""
        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.transient(parent)
        dialog.grab_set()
        dialog.resizable(False, False)

        result = None
        
        main_frame = ttk.Frame(dialog, padding="15")
        main_frame.pack(expand=True, fill="both")

        ttk.Label(main_frame, text=prompt).pack(pady=(0, 10), anchor='w')
        
        entry = ttk.Entry(main_frame, width=40, font=self.font_normal)
        entry.pack(pady=5, fill='x', expand=True)
        entry.focus_set()

        def on_ok():
            nonlocal result
            result = entry.get()
            dialog.destroy()

        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill='x', pady=(15, 0))
        
        ttk.Button(buttons_frame, text=self.translate("accept"), command=on_ok, style="Custom.TButton").pack(side="right")
        ttk.Button(buttons_frame, text=self.translate("cancel"), command=dialog.destroy, style="Custom.TButton").pack(side="right", padx=5)

        dialog.bind("<Return>", lambda event: on_ok())
        dialog.bind("<Escape>", lambda event: dialog.destroy())

        dialog.update_idletasks()
        root_x, root_y, root_width, root_height = parent.winfo_x(), parent.winfo_y(), parent.winfo_width(), parent.winfo_height()
        win_width, win_height = dialog.winfo_width(), dialog.winfo_height()
        pos_x = root_x + (root_width // 2) - (win_width // 2)
        pos_y = root_y + (root_height // 2) - (win_height // 2)
        dialog.geometry(f"+{pos_x}+{pos_y}")
        parent.wait_window(dialog)
        return result

    def open_edit_level_window(self):
        """Abre una ventana para editar los metadatos del nivel actual."""
        win = tk.Toplevel(self.root)
        win.title(self.translate("edit_level_title").format(filename=self.current_file_name))
        win.transient(self.root)
        win.grab_set()
        win.resizable(False, False)

        frame = ttk.Frame(win, padding="15")
        frame.pack(expand=True, fill="both")
        frame.columnconfigure(1, weight=1)

        fields = {
            self.translate("level_id"): tk.StringVar(value=self.current_file_content.get("id", "")),
            self.translate("level_name"): tk.StringVar(value=self.current_file_content.get("name", "")),
            self.translate("level_author"): tk.StringVar(value=self.current_file_content.get("author", "")),
            self.translate("level_verifier"): tk.StringVar(value=self.current_file_content.get("verifier", "")),
            self.translate("level_creators"): tk.StringVar(value=", ".join(map(str, self.current_file_content.get("creators", [])))),
            self.translate("level_verification_link"): tk.StringVar(value=self.current_file_content.get("verification", "")),
            self.translate("level_percent_qualify"): tk.StringVar(value=self.current_file_content.get("percentToQualify", "100"))
        }

        for i, (label_text, var) in enumerate(fields.items()):
            ttk.Label(frame, text=f"{label_text}:", font=self.font_normal).grid(row=i, column=0, sticky="w", pady=4, padx=(0,10))
            entry = ttk.Entry(frame, textvariable=var, width=50, font=self.font_normal)
            entry.grid(row=i, column=1, sticky="ew", padx=5, pady=4)
        
        def save_edited_level():
            try:
                id_val = int(fields[self.translate("level_id")].get().strip())
                name = fields[self.translate("level_name")].get().strip()
                percent_val = int(fields[self.translate("level_percent_qualify")].get().strip())
                creators_list = [c.strip() for c in fields[self.translate("level_creators")].get().strip().split(',') if c.strip()]

                content_dict = {
                    "id": id_val, "name": name,
                    "author": fields["Autor"].get().strip(),
                    "verifier": fields["Verificador"].get().strip(),
                    "creators": creators_list,
                    "verification": fields["Link de Verificación"].get().strip(),
                    "percentToQualify": percent_val,
                    "records": self.current_file_content.get("records", [])
                }
                content_json = json.dumps(content_dict, indent=2, ensure_ascii=False)
                encoded_content = base64.b64encode(content_json.encode('utf-8')).decode('utf-8')

                owner, repo = self.parse_github_url(self.repo_url_entry.get())
                token = self.github_token
                file_path = f"{self.folder_entry.get()}/{self.current_file_name}"
                api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
                headers = {'Authorization': f'token {token}'}
                commit_data = { "message": self.translate("commit_update_metadata").format(filename=self.current_file_name), "content": encoded_content, "sha": self.current_file_sha }

                response = requests.put(api_url, headers=headers, json=commit_data)
                response.raise_for_status()

                win.destroy()
                self.load_file_content(self.current_file_name) # Recargar para obtener nuevo SHA
                messagebox.showinfo(self.translate("success"), self.translate("success_metadata_updated"))

            except ValueError:
                messagebox.showerror(self.translate("error"), self.translate("error_id_percent_integer"), parent=win)
            except requests.exceptions.RequestException as e:
                messagebox.showerror(self.translate("error"), self.translate("error_saving_changes").format(error=str(e)), parent=win)
            except Exception as e:
                messagebox.showerror(self.translate("error"), self.translate("error_unexpected").format(error=str(e)), parent=win)

        def delete_level():
            if not messagebox.askyesno(self.translate("confirm_deletion"), self.translate("confirm_delete_level").format(filename=self.current_file_name), parent=win):
                return
            try:
                owner, repo = self.parse_github_url(self.repo_url_entry.get())
                token = self.github_token
                file_path = f"{self.folder_entry.get()}/{self.current_file_name}"
                api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
                headers = {'Authorization': f'token {token}'}
                commit_data = { "message": self.translate("commit_delete_level").format(filename=self.current_file_name), "sha": self.current_file_sha }

                response = requests.delete(api_url, headers=headers, json=commit_data)
                response.raise_for_status()

                messagebox.showinfo(self.translate("success"), self.translate("success_file_deleted").format(filename=self.current_file_name))
                win.destroy()
                self.current_file_name = None
                self.current_file_content = None
                self.current_file_sha = None
                self.populate_records_treeview()
                self.update_contextual_button_states()
                self.load_github_files()
            except requests.exceptions.RequestException as e:
                messagebox.showerror(self.translate("error"), self.translate("error_deleting_file").format(error=str(e)), parent=win)
            except Exception as e:
                messagebox.showerror(self.translate("error"), self.translate("error_unexpected").format(error=str(e)), parent=win)

        buttons_frame = ttk.Frame(frame)
        buttons_frame.grid(row=len(fields), column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(buttons_frame, text=self.translate("delete_level"), command=delete_level, style="Custom.TButton").pack(side="left")
        ttk.Button(buttons_frame, text=self.translate("save_changes"), command=save_edited_level, style="Custom.TButton").pack(side="right")
        ttk.Button(buttons_frame, text=self.translate("cancel"), command=win.destroy, style="Custom.TButton").pack(side="right", padx=5)

        win.update_idletasks()
        root_x, root_y, root_width, root_height = self.root.winfo_x(), self.root.winfo_y(), self.root.winfo_width(), self.root.winfo_height()
        win_width, win_height = win.winfo_width(), win.winfo_height()
        pos_x = root_x + (root_width // 2) - (win_width // 2)
        pos_y = root_y + (root_height // 2) - (win_height // 2)
        win.geometry(f"+{pos_x}+{pos_y}")
        win.focus_set()

    def open_add_level_window(self):
        """Abre una ventana emergente para añadir un nuevo nivel (archivo JSON)."""
        if not self.repo_url_entry.get() or not self.folder_entry.get():
            messagebox.showwarning(self.translate("warning"), self.translate("warn_config_repo_folder"))
            return

        win = tk.Toplevel(self.root)
        win.title(self.translate("add_new_level"))
        win.transient(self.root)
        win.grab_set()
        win.resizable(False, False)

        frame = ttk.Frame(win, padding="15")
        frame.pack(expand=True, fill="both")
        frame.columnconfigure(1, weight=1)

        fields = {
            self.translate("level_id"): tk.StringVar(),
            self.translate("level_name"): tk.StringVar(),
            self.translate("level_author"): tk.StringVar(),
            self.translate("level_verifier"): tk.StringVar(),
            self.translate("level_creators"): tk.StringVar(),
            self.translate("level_verification_link"): tk.StringVar(),
            self.translate("level_percent_qualify"): tk.StringVar(value="100")
        }

        for i, (label_text, var) in enumerate(fields.items()):
            ttk.Label(frame, text=f"{label_text}:", font=self.font_normal).grid(row=i, column=0, sticky="w", pady=4, padx=(0,10))
            entry = ttk.Entry(frame, textvariable=var, width=50, font=self.font_normal)
            entry.grid(row=i, column=1, sticky="ew", padx=5, pady=4)
        
        def import_from_aredl():
            level_id = self._custom_ask_string(self.translate("import_from_aredl"), self.translate("aredl_import_prompt"), win)
            if not level_id or not level_id.strip().isdigit():
                if level_id is not None: # No mostrar alerta si el usuario cancela
                    messagebox.showwarning(self.translate("invalid_input"), self.translate("numeric_id_required"), parent=win)
                return

            level_id = level_id.strip()
            API_BASE = 'https://api.aredl.net/v2/api/aredl/levels'

            try:
                # Obtener información principal del nivel
                info_resp = requests.get(f"{API_BASE}/{level_id}")
                info_resp.raise_for_status()
                info = info_resp.json()

                # Obtener creadores
                creators_resp = requests.get(f"{API_BASE}/{level_id}/creators")
                creators_resp.raise_for_status()
                creators_data = creators_resp.json()

                # Rellenar campos
                fields[self.translate("level_id")].set(info.get('level_id', ''))
                fields[self.translate("level_name")].set(info.get('name', ''))
                fields[self.translate("level_author")].set(info.get('publisher', {}).get('global_name', ''))
                
                verifications = info.get('verifications')
                fields[self.translate("level_verifier")].set(verifications[0].get('submitted_by', {}).get('global_name', '') if verifications else '')
                fields[self.translate("level_verification_link")].set(verifications[0].get('video_url', '') if verifications else '')

                creator_names = [c.get('global_name') for c in creators_data if c.get('global_name')]
                fields[self.translate("level_creators")].set(", ".join(creator_names) if creator_names else info.get('publisher', {}).get('global_name', ''))

                fields[self.translate("level_percent_qualify")].set("100")
                messagebox.showinfo(self.translate("success"), self.translate("success_aredl_import"), parent=win)

            except requests.exceptions.HTTPError as e:
                messagebox.showerror(self.translate("api_error"), self.translate("api_error_details").format(code=e.response.status_code, level_id=level_id), parent=win)
            except requests.exceptions.RequestException as e:
                messagebox.showerror(self.translate("network_error"), self.translate("network_error_details").format(e=e), parent=win)
            except Exception as e:
                messagebox.showerror(self.translate("error"), self.translate("error_unexpected").format(error=e), parent=win)

        def save_new_level():
            try:
                # 1. Get and validate data
                id_str = fields[self.translate("level_id")].get().strip()
                name = fields[self.translate("level_name")].get().strip()
                author = fields[self.translate("level_author")].get().strip()
                verifier = fields[self.translate("level_verifier")].get().strip()
                creators_str = fields[self.translate("level_creators")].get().strip()
                verification = fields[self.translate("level_verification_link")].get().strip()
                percent_str = fields[self.translate("level_percent_qualify")].get().strip()

                if not all([id_str, name, author, verifier, verification, percent_str]):
                    messagebox.showerror(self.translate("error"), self.translate("all_fields_mandatory"), parent=win)
                    return
                
                id_val = int(id_str)
                percent_val = int(percent_str)
                
                creators_list = [c.strip() for c in creators_str.split(',') if c.strip()]
                
                # 2. Create filename
                safe_name = re.sub(r'[^a-z0-9_]', '', name.lower().replace(' ', '_'))
                if not safe_name:
                    messagebox.showerror(self.translate("error"), self.translate("invalid_level_name_filename"), parent=win)
                    return
                file_name = f"{safe_name}.json"

                # 3. Check if file exists in loaded list
                if hasattr(self, 'display_files') and self.display_files and any(d['name'].lower() == file_name.lower() for d in self.display_files):
                    messagebox.showerror(self.translate("error"), self.translate("file_already_exists").format(filename=file_name), parent=win)
                    return

                # 4. Construct JSON
                content_dict = { "id": id_val, "name": name, "author": author, "verifier": verifier, "creators": creators_list, "verification": verification, "percentToQualify": percent_val, "records": [] }
                content_json = json.dumps(content_dict, indent=2, ensure_ascii=False)
                encoded_content = base64.b64encode(content_json.encode('utf-8')).decode('utf-8')

                # 5. Commit to GitHub
                owner, repo = self.parse_github_url(self.repo_url_entry.get())
                token = self.github_token
                if not token:
                    messagebox.showerror(self.translate("error"), self.translate("token_needed_to_create"), parent=win)
                    return

                file_path = f"{self.folder_entry.get()}/{file_name}"
                api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
                headers = {'Authorization': f'token {token}'}
                commit_data = { "message": self.translate("commit_add_level").format(name=name), "content": encoded_content }

                response = requests.put(api_url, headers=headers, json=commit_data)
                response.raise_for_status()
                
                messagebox.showinfo(self.translate("success"), self.translate("success_level_added").format(name=name, filename=file_name))
                win.destroy()
                self.load_github_files() # Refresh the list

            except ValueError:
                messagebox.showerror(self.translate("error"), self.translate("error_id_percent_integer"), parent=win)
            except requests.exceptions.RequestException as e:
                messagebox.showerror(self.translate("error"), self.translate("error_creating_file").format(error=str(e)), parent=win)
            except Exception as e:
                messagebox.showerror(self.translate("error"), self.translate("error_unexpected").format(error=str(e)), parent=win)

        buttons_frame = ttk.Frame(frame)
        buttons_frame.grid(row=len(fields), column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(buttons_frame, text=self.translate("import_from_aredl"), command=import_from_aredl, style="Custom.TButton").pack(side="left")
        ttk.Button(buttons_frame, text=self.translate("save"), command=save_new_level, style="Custom.TButton").pack(side="right")
        ttk.Button(buttons_frame, text=self.translate("cancel"), command=win.destroy, style="Custom.TButton").pack(side="right", padx=5)

        win.update_idletasks()
        root_x, root_y, root_width, root_height = self.root.winfo_x(), self.root.winfo_y(), self.root.winfo_width(), self.root.winfo_height()
        win_width, win_height = win.winfo_width(), win.winfo_height()
        pos_x = root_x + (root_width // 2) - (win_width // 2)
        pos_y = root_y + (root_height // 2) - (win_height // 2)
        win.geometry(f"+{pos_x}+{pos_y}")
        win.focus_set()

    def open_list_updater(self):
        """Abre una ventana para seleccionar un archivo de orden de la lista de GitHub."""
        if not hasattr(self, 'display_files') or not self.display_files:
            messagebox.showwarning(self.translate("warning"), self.translate("warn_load_files_first"))
            return

        # Create the selection window
        select_win = tk.Toplevel(self.root)
        select_win.title(self.translate("select_order_file"))
        select_win.transient(self.root)
        select_win.grab_set()
        select_win.resizable(False, False)

        main_frame = ttk.Frame(select_win, padding="10")
        main_frame.pack(expand=True, fill="both")

        ttk.Label(main_frame, text=self.translate("select_order_file_label")).pack(pady=(0, 5), anchor='w')

        listbox = tk.Listbox(main_frame, font=self.font_normal, height=10)
        listbox.pack(expand=True, fill="both", pady=5)

        for item in self.display_files:
            listbox.insert(tk.END, item["name"])

        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill="x", pady=(10, 0))

        def on_select():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning(self.translate("warning"), self.translate("warn_select_file"), parent=select_win)
                return
            
            file_name = listbox.get(selection[0])
            select_win.destroy() # Close this window before opening the next
            self.load_and_show_reorder_window(file_name)

        ttk.Button(buttons_frame, text=self.translate("select"), command=on_select, style="Custom.TButton").pack(side="right")
        ttk.Button(buttons_frame, text=self.translate("cancel"), command=select_win.destroy, style="Custom.TButton").pack(side="right", padx=5)

        # Center the window
        select_win.update_idletasks()
        root_x, root_y, root_width, root_height = self.root.winfo_x(), self.root.winfo_y(), self.root.winfo_width(), self.root.winfo_height()
        win_width, win_height = select_win.winfo_width(), select_win.winfo_height()
        pos_x = root_x + (root_width // 2) - (win_width // 2)
        pos_y = root_y + (root_height // 2) - (win_height // 2)
        select_win.geometry(f"+{pos_x}+{pos_y}")
        select_win.focus_set()

    def load_and_show_reorder_window(self, file_name):
        """Carga el contenido de un archivo de orden desde GitHub y abre la ventana de reordenamiento."""
        owner, repo = self.parse_github_url(self.repo_url)
        token = self.github_token
        file_path_api = f"{self.folder_path}/{file_name}"
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path_api}"
        headers = {'Authorization': f'token {token}'} if token else {}
        
        try:
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            file_data = response.json()
            content = base64.b64decode(file_data['content']).decode('utf-8')
            order_list = json.loads(content)
            if not isinstance(order_list, list) or not all(isinstance(item, str) for item in order_list):
                messagebox.showerror(self.translate("format_error"), self.translate("format_error_details").format(filename=file_name))
                return
            self.open_reorder_window(order_list)
        except requests.exceptions.RequestException as e:
            messagebox.showerror(self.translate("error"), self.translate("error_loading_order_file").format(str(e)))
        except json.JSONDecodeError:
            messagebox.showerror(self.translate("file_error"), self.translate("file_error_details").format(filename=file_name))
        except Exception as e:
            messagebox.showerror(self.translate("error"), self.translate("error_processing_order_file").format(str(e)))

    def open_reorder_window(self, order_list):
        """Abre una ventana para reordenar una lista de items."""
        reorder_win = tk.Toplevel(self.root)
        reorder_win.title(self.translate("reorder_list"))
        reorder_win.transient(self.root)
        reorder_win.grab_set()
        reorder_win.minsize(400, 500)

        main_frame = ttk.Frame(reorder_win, padding="10")
        main_frame.pack(expand=True, fill="both")
        main_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        list_frame = ttk.Frame(main_frame)
        list_frame.grid(row=0, column=0, columnspan=2, sticky='nsew')
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        listbox = tk.Listbox(list_frame, font=self.font_normal)
        listbox.grid(row=0, column=0, sticky='nsew')
        
        for i, item in enumerate(order_list):
            listbox.insert(tk.END, f"{i + 1}. {item}")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        listbox.config(yscrollcommand=scrollbar.set)

        def renumber_list():
            for i in range(listbox.size()):
                item_text = listbox.get(i)
                name = ". ".join(item_text.split(". ")[1:])
                listbox.delete(i)
                listbox.insert(i, f"{i + 1}. {name}")

        def add_item():
            new_item_name = self._custom_ask_string(self.translate("add_level"), self.translate("level_name") + ":", reorder_win)
            if new_item_name and new_item_name.strip():
                listbox.insert(tk.END, f"0. {new_item_name.strip()}") # Número temporal
                renumber_list()
                listbox.selection_set(tk.END)
                listbox.see(tk.END)
        
        def delete_item():
            selection_indices = listbox.curselection()
            if not selection_indices:
                messagebox.showwarning(self.translate("warning"), self.translate("warn_select_record_delete"), parent=reorder_win)
                return
            
            if messagebox.askyesno(self.translate("confirm_deletion"), self.translate("confirm_delete_record"), parent=reorder_win):
                listbox.delete(selection_indices[0])
                renumber_list()

        def move_item(direction):
            selection_indices = listbox.curselection()
            if not selection_indices: return
            selected_index = selection_indices[0]
            
            if direction == 'up' and selected_index > 0: new_index = selected_index - 1
            elif direction == 'down' and selected_index < listbox.size() - 1: new_index = selected_index + 1
            else: return

            item = listbox.get(selected_index)
            listbox.delete(selected_index)
            listbox.insert(new_index, item)
            renumber_list()

            # Restaurar la selección en la nueva posición para no perder el foco
            listbox.selection_set(new_index)
            listbox.activate(new_index)
            listbox.see(new_index)

        def apply_changes():
            final_order = [".".join(listbox.get(i).split(". ")[1:]) for i in range(listbox.size())]
            original_records = self.current_file_content.get('records', [])
            records_map = {record['user']: record for record in original_records}
            new_records_list = []
            users_in_original_records = set(records_map.keys())
            
            for user in final_order:
                if user in records_map:
                    new_records_list.append(records_map[user])
                    if user in users_in_original_records: users_in_original_records.remove(user)
            
            for user in sorted(list(users_in_original_records)): new_records_list.append(records_map[user])

            self.current_file_content['records'] = new_records_list
            self.populate_records_treeview()
            messagebox.showinfo(self.translate("success"), self.translate("success_list_reordered"), parent=reorder_win)
            reorder_win.destroy()

        move_buttons_frame = ttk.Frame(main_frame)
        move_buttons_frame.grid(row=1, column=0, pady=(10,0), sticky='w')
        ttk.Button(move_buttons_frame, text=self.translate("up"), command=lambda: move_item('up')).pack(side='left')
        ttk.Button(move_buttons_frame, text=self.translate("down"), command=lambda: move_item('down')).pack(side='left', padx=5)
        ttk.Button(move_buttons_frame, text=self.translate("add"), command=add_item).pack(side='left', padx=(20, 5))
        ttk.Button(move_buttons_frame, text=self.translate("delete"), command=delete_item).pack(side='left')

        action_buttons_frame = ttk.Frame(main_frame)
        action_buttons_frame.grid(row=1, column=1, pady=(10,0), sticky='e')
        ttk.Button(action_buttons_frame, text=self.translate("save_apply"), command=apply_changes).pack(side='right')
        ttk.Button(action_buttons_frame, text=self.translate("cancel"), command=reorder_win.destroy).pack(side='right', padx=5)

        reorder_win.update_idletasks()
        root_x, root_y, root_width, root_height = self.root.winfo_x(), self.root.winfo_y(), self.root.winfo_width(), self.root.winfo_height()
        win_width, win_height = reorder_win.winfo_width(), reorder_win.winfo_height()
        pos_x = root_x + (root_width // 2) - (win_width // 2)
        pos_y = root_y + (root_height // 2) - (win_height // 2)
        reorder_win.geometry(f"{win_width}x{win_height}+{pos_x}+{pos_y}")
        reorder_win.focus_set()

    def open_text_editor(self):
        """Abre un editor de texto para modificar el JSON manualmente."""
        editor_win = tk.Toplevel(self.root)
        editor_win.title(self.translate("text_editor_title").format(filename=self.current_file_name))
        editor_win.transient(self.root)
        editor_win.grab_set()
        editor_win.geometry("800x600")
        editor_win.rowconfigure(0, weight=1)
        editor_win.columnconfigure(0, weight=1)

        text_editor = scrolledtext.ScrolledText(editor_win, wrap=tk.WORD, font=self.font_mono)
        text_editor.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))

        formatted_json = json.dumps(self.current_file_content, indent=2, ensure_ascii=False)
        text_editor.insert(1.0, formatted_json)

        buttons_frame = ttk.Frame(editor_win, padding="10")
        buttons_frame.grid(row=1, column=0, sticky="ew")

        def save_and_close():
            try:
                new_content_str = text_editor.get(1.0, tk.END)
                new_content_dict = json.loads(new_content_str)
                
                self.current_file_content = new_content_dict
                self.populate_records_treeview()
                
                messagebox.showinfo(self.translate("success"), self.translate("success_content_updated_memory"), parent=editor_win)
                editor_win.destroy()
                
            except json.JSONDecodeError as e:
                messagebox.showerror(self.translate("json_error"), self.translate("json_error_details").format(e=e), parent=editor_win)
            except Exception as e:
                messagebox.showerror(self.translate("error"), self.translate("error_unexpected").format(error=e), parent=editor_win)

        ttk.Button(buttons_frame, text=self.translate("save_close"), command=save_and_close, style="Custom.TButton").pack(side="right")
        ttk.Button(buttons_frame, text=self.translate("cancel"), command=editor_win.destroy, style="Custom.TButton").pack(side="right", padx=5)

        editor_win.update_idletasks()
        root_x, root_y, root_width, root_height = self.root.winfo_x(), self.root.winfo_y(), self.root.winfo_width(), self.root.winfo_height()
        win_width, win_height = editor_win.winfo_width(), editor_win.winfo_height()
        pos_x = root_x + (root_width // 2) - (win_width // 2)
        pos_y = root_y + (root_height // 2) - (win_height // 2)
        editor_win.geometry(f"800x600+{pos_x}+{pos_y}")
        editor_win.focus_set()

    def save_changes(self):
        """Guarda los cambios en GitHub"""
        owner, repo = self.parse_github_url(self.repo_url)
        token = self.github_token
        
        if not token:
            messagebox.showwarning(self.translate("warning"), self.translate("token_needed_to_save"))
            return
        
        file_path = f"{self.folder_path}/{self.current_file_name}"
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
        
        # Primero obtener el SHA del archivo actual
        headers = {'Authorization': f'token {token}'}
        
        try:
            # Obtener información del archivo actual
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            current_file_info = response.json()
            sha = current_file_info['sha']
            
            # Preparar datos para el commit
            content = json.dumps(self.current_file_content, indent=2, ensure_ascii=False)
            encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            commit_data = {
                "message": self.translate("commit_update_records").format(filename=self.current_file_name),
                "content": encoded_content,
                "sha": sha
            }
            
            # Hacer el commit
            response = requests.put(api_url, headers=headers, json=commit_data)
            response.raise_for_status()
            
            messagebox.showinfo(self.translate("success"), self.translate("success_changes_saved_github"))
            
        except requests.exceptions.RequestException as e:
            messagebox.showerror(self.translate("error"), self.translate("error_saving_changes").format(error=str(e)))
        except Exception as e:
            messagebox.showerror(self.translate("error"), self.translate("error_unexpected").format(error=str(e)))

def main():
    root = tk.Tk()
    app = GitHubJSONEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()