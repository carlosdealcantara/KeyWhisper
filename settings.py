import os
import json
import customtkinter as ctk
from tkinter import filedialog

CONFIG_DIR = os.path.join(os.environ.get('APPDATA', ''), 'KeyWhisper')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')

DEFAULT_CONFIG = {
    "file_path": "",
    "hotkey": "f9",
    "bridge_enabled": True,
    "toast_enabled": True,
    "show_welcome_on_startup": True
}

def load_config():
    if not os.path.exists(CONFIG_DIR):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
        except Exception:
            pass

    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            # Preenche chaves faltantes caso o arquivo seja antigo
            for k, v in DEFAULT_CONFIG.items():
                if k not in config:
                    config[k] = v
            return config
    except Exception as e:
        print(f"[Config] Erro ao carregar configurações: {e}")
        return DEFAULT_CONFIG

def save_config(config):
    if not os.path.exists(CONFIG_DIR):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
        except Exception:
            pass
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[Config] Erro ao salvar configurações: {e}")


class SettingsWindow:
    def __init__(self, parent_root, on_save_callback=None):
        self.parent_root = parent_root
        self.on_save_callback = on_save_callback
        self.window = None
        self.config = load_config()

        # Cores e Estilos Premium
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

    def show(self):
        if self.window and self.window.winfo_exists():
            self.window.focus()
            return

        self.window = ctk.CTkToplevel(self.parent_root)
        self.window.title("KeyWhisper v2.0 - Configurações")
        self.window.geometry("580x500")
        self.window.resizable(False, False)
        
        # Garante foco e centralização
        self.window.grab_set()
        self.window.focus()
        
        # Centraliza na tela
        self.window.update_idletasks()
        width = 580
        height = 500
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

        # Título principal com gradiente visual fictício (Uso de cores fortes)
        title_label = ctk.CTkLabel(
            self.window, 
            text="KEYWHISPER v2.0", 
            font=ctk.CTkFont(family="Inter", size=24, weight="bold"),
            text_color="#10b981" # Esmeralda elegante
        )
        title_label.pack(pady=(20, 5))

        subtitle_label = ctk.CTkLabel(
            self.window, 
            text="Ponte de Injeção de Texto Inteligente", 
            font=ctk.CTkFont(family="Inter", size=13),
            text_color="#9ca3af"
        )
        subtitle_label.pack(pady=(0, 20))

        # Container Principal
        container = ctk.CTkFrame(self.window, fg_color="#1f2937", corner_radius=12)
        container.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # --- Linha 1: Arquivo Monitorado ---
        file_label = ctk.CTkLabel(
            container, 
            text="Arquivo de saída do WhisperDesktop (.txt):", 
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            text_color="#f3f4f6"
        )
        file_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(15, 5))

        self.file_entry = ctk.CTkEntry(
            container, 
            width=360, 
            height=32,
            fg_color="#374151", 
            text_color="#f9fafb",
            border_color="#4b5563"
        )
        self.file_entry.grid(row=1, column=0, padx=(15, 10), pady=(0, 15), sticky="w")
        self.file_entry.insert(0, self.config.get("file_path", ""))

        browse_btn = ctk.CTkButton(
            container, 
            text="Procurar...", 
            width=100, 
            height=32,
            fg_color="#10b981",
            hover_color="#059669",
            text_color="#ffffff",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            command=self._browse_file
        )
        browse_btn.grid(row=1, column=1, padx=(0, 15), pady=(0, 15), sticky="e")

        # --- Linha 2: Hotkey ---
        hotkey_label = ctk.CTkLabel(
            container, 
            text="Tecla de ativação (Toggle da Ponte):", 
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            text_color="#f3f4f6"
        )
        hotkey_label.grid(row=2, column=0, sticky="w", padx=15, pady=(0, 5))

        self.hotkey_entry = ctk.CTkEntry(
            container, 
            width=150, 
            height=32,
            fg_color="#374151", 
            text_color="#f9fafb",
            border_color="#4b5563"
        )
        self.hotkey_entry.grid(row=3, column=0, padx=15, pady=(0, 15), sticky="w")
        self.hotkey_entry.insert(0, self.config.get("hotkey", "f9"))

        # --- Linha 3: Toggles ---
        self.bridge_switch = ctk.CTkSwitch(
            container, 
            text="Iniciar com a ponte ativa", 
            progress_color="#10b981",
            text_color="#e5e7eb",
            font=ctk.CTkFont(family="Inter", size=13)
        )
        self.bridge_switch.grid(row=4, column=0, columnspan=2, padx=15, pady=(5, 5), sticky="w")
        if self.config.get("bridge_enabled", True):
            self.bridge_switch.select()

        self.toast_switch = ctk.CTkSwitch(
            container, 
            text="Mostrar notificações flutuantes ao digitar", 
            progress_color="#10b981",
            text_color="#e5e7eb",
            font=ctk.CTkFont(family="Inter", size=13)
        )
        self.toast_switch.grid(row=5, column=0, columnspan=2, padx=15, pady=(5, 5), sticky="w")
        if self.config.get("toast_enabled", True):
            self.toast_switch.select()

        # --- Linha 4: Dica de Desempenho ---
        tip_frame = ctk.CTkFrame(container, fg_color="#374151", corner_radius=8)
        tip_frame.grid(row=6, column=0, columnspan=2, padx=15, pady=(5, 15), sticky="ew")
        
        tip_label = ctk.CTkLabel(
            tip_frame,
            text="⚡ Como acelerar a digitação:\nNas configurações do Whisper Desktop, utilize um modelo menor (ex: 'Base' ou 'Small') e certifique-se de ativar a aceleração por GPU (DirectCompute/OpenCL) nas configurações do Whisper. Isso reduz o tempo de processamento de segundos para milissegundos!",
            font=ctk.CTkFont(family="Inter", size=11),
            text_color="#9ca3af",
            justify="left",
            wraplength=510
        )
        tip_label.pack(padx=10, pady=8)

        # Botão de Ação / Salvar
        btn_container = ctk.CTkFrame(self.window, fg_color="transparent")
        btn_container.pack(fill="x", padx=20, pady=(0, 15))

        # Botão Abrir Pasta do WhisperDesktop
        open_folder_btn = ctk.CTkButton(
            btn_container,
            text="Testar Arquivo",
            width=120,
            height=36,
            fg_color="#374151",
            hover_color="#4b5563",
            text_color="#ffffff",
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            command=self._test_file
        )
        open_folder_btn.pack(side="left")

        save_btn = ctk.CTkButton(
            btn_container, 
            text="Salvar Configurações", 
            width=180, 
            height=36,
            fg_color="#10b981",
            hover_color="#059669",
            text_color="#ffffff",
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            command=self._save_settings
        )
        save_btn.pack(side="right")

    def _browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Selecione o arquivo de saída do WhisperDesktop",
            filetypes=[("Arquivos de Texto", "*.txt"), ("Todos os Arquivos", "*.*")]
        )
        if file_path:
            self.file_entry.delete(0, ctk.END)
            self.file_entry.insert(0, file_path)

    def _test_file(self):
        path = self.file_entry.get().strip()
        if not path:
            return
        
        # Se o arquivo não existe, tenta criar para o usuário testar
        if not os.path.exists(path):
            try:
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write("")
            except Exception:
                pass
        
        # Abre o arquivo no bloco de notas padrão para verificação
        try:
            os.startfile(path)
        except Exception:
            pass

    def _save_settings(self):
        # Remove aspas externas (duplas ou simples) e espaços extras
        raw_path = self.file_entry.get().strip()
        clean_path = raw_path.strip('"').strip("'").strip()

        new_config = {
            "file_path": clean_path,
            "hotkey": self.hotkey_entry.get().strip().lower(),
            "bridge_enabled": bool(self.bridge_switch.get()),
            "toast_enabled": bool(self.toast_switch.get())
        }

        save_config(new_config)
        
        if self.on_save_callback:
            self.on_save_callback(new_config)

        self.window.grab_release()
        self.window.destroy()
        self.window = None
