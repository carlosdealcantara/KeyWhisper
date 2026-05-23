import os
import json
import customtkinter as ctk
import subprocess
import threading
import time

CONFIG_DIR = os.path.join(os.environ.get('APPDATA', ''), 'KeyWhisper')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
MODELS_DIR = os.path.join(CONFIG_DIR, 'models')
OUTPUT_DIR = os.path.join(CONFIG_DIR, 'output')
DEFAULT_TRANSCRIPT = os.path.join(OUTPUT_DIR, 'transcript.kwtmp')

DEFAULT_CONFIG = {
    "file_path": DEFAULT_TRANSCRIPT,
    "hotkey": "f9",
    "bridge_enabled": False,
    "toast_enabled": True,
    "show_welcome_on_startup": True,
    "auto_startup": True,
    "model_name": "ggml-small.bin",
    "language": "pt",
    "gpu_acceleration": True,
    "step_ms": 500,
    "length_ms": 5000
}

# Mapeamentos amigáveis
LANGUAGES = {
    "Português (pt)": "pt",
    "Inglês (en)": "en",
    "Espanhol (es)": "es",
    "Detecção Automática": "auto"
}
LANGUAGES_REV = {v: k for k, v in LANGUAGES.items()}


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
        with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
            config = json.load(f)
            # Garante que chaves novas sejam preenchidas com os padrões
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

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

    def show(self):
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return

        self.window = ctk.CTkToplevel(self.parent_root)
        self.window.title("KeyWhisper v2.0 - Configurações")
        self.window.geometry("620x620")
        self.window.resizable(False, False)
        
        # Garante foco absoluto — aparece acima de qualquer outra janela do app
        self.window.attributes("-topmost", True)
        self.window.grab_set()
        self.window.after(200, lambda: (
            self.window.attributes("-topmost", False),
            self.window.lift(),
            self.window.focus_force()
        ) if self.window and self.window.winfo_exists() else None)
        
        # Centralização responsiva na tela
        self.window.update_idletasks()
        width = 620
        height = 620
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

        # Cabeçalho Principal Premium
        header_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        header_frame.pack(fill="x", pady=(20, 10))
        
        title_label = ctk.CTkLabel(
            header_frame, 
            text="KEYWHISPER v2.0", 
            font=ctk.CTkFont(family="Outfit", size=26, weight="bold"),
            text_color="#10b981"  # Verde esmeralda premium
        )
        title_label.pack()

        subtitle_label = ctk.CTkLabel(
            header_frame, 
            text="Painel de Controle e Inteligência Artificial", 
            font=ctk.CTkFont(family="Inter", size=13),
            text_color="#9ca3af"
        )
        subtitle_label.pack()

        # Frame de Rolagem para acomodar todas as seções perfeitamente em qualquer DPI
        self.scroll_container = ctk.CTkScrollableFrame(
            self.window, 
            fg_color="#1f2937", 
            corner_radius=12,
            scrollbar_button_color="#4b5563",
            scrollbar_button_hover_color="#6b7280"
        )
        self.scroll_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # --- SEÇÃO 1: CONFIGURAÇÕES GERAIS ---
        sec1_label = ctk.CTkLabel(
            self.scroll_container,
            text="Configurações Gerais",
            font=ctk.CTkFont(family="Inter", size=15, weight="bold"),
            text_color="#10b981"
        )
        sec1_label.pack(anchor="w", padx=15, pady=(15, 10))

        # Grid para inputs gerais
        general_grid = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        general_grid.pack(fill="x", padx=15, pady=0)
        general_grid.columnconfigure(1, weight=1)

        # Idioma Dropdown
        lang_label = ctk.CTkLabel(
            general_grid,
            text="Voz e transcrição:",
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            text_color="#f3f4f6"
        )
        lang_label.grid(row=0, column=0, sticky="w", pady=8, padx=(0, 15))
        
        current_lang_code = self.config.get("language", "pt")
        current_lang_name = LANGUAGES_REV.get(current_lang_code, "Português (pt)")
        
        self.lang_menu = ctk.CTkOptionMenu(
            general_grid,
            values=list(LANGUAGES.keys()),
            fg_color="#374151",
            button_color="#10b981",
            button_hover_color="#059669",
            dropdown_fg_color="#1f2937",
            dropdown_text_color="#f9fafb",
            font=ctk.CTkFont(family="Inter", size=12),
            dropdown_font=ctk.CTkFont(family="Inter", size=12)
        )
        self.lang_menu.set(current_lang_name)
        self.lang_menu.grid(row=0, column=1, sticky="ew", pady=8)

        # Tecla de Atalho (Hotkey)
        hotkey_label = ctk.CTkLabel(
            general_grid,
            text="Tecla de Digitação (Ativar):",
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            text_color="#f3f4f6"
        )
        hotkey_label.grid(row=1, column=0, sticky="w", pady=8, padx=(0, 15))

        self.hotkey_entry = ctk.CTkEntry(
            general_grid,
            fg_color="#374151",
            text_color="#f9fafb",
            border_color="#4b5563",
            height=32,
            font=ctk.CTkFont(family="Consolas", size=13)
        )
        self.hotkey_entry.insert(0, self.config.get("hotkey", "f9"))
        self.hotkey_entry.grid(row=1, column=1, sticky="ew", pady=8)

        # Switches de Status


        self.startup_switch = ctk.CTkSwitch(
            self.scroll_container,
            text="Iniciar automaticamente com o Windows (Silencioso)",
            progress_color="#10b981",
            text_color="#e5e7eb",
            font=ctk.CTkFont(family="Inter", size=13)
        )
        self.startup_switch.pack(anchor="w", padx=15, pady=8)
        if self.config.get("auto_startup", True):
             self.startup_switch.select()

        # --- SEÇÃO 2: MOTOR DE IA E MODELO ---
        # Removido título "Motor de IA e Modelo" conforme pedido para otimizar espaço
        self.model_status_label = ctk.CTkLabel(
            self.scroll_container,
            text="Verificando...",
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            text_color="#9ca3af",
            justify="left"
        )
        self.model_status_label.pack(anchor="w", padx=15, pady=(15, 8))

        self.download_btn = ctk.CTkButton(
            self.scroll_container,
            text="Baixar Componentes de IA",
            fg_color="#3b82f6",
            hover_color="#2563eb",
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            height=36,
            command=self._start_download
        )
        self.download_btn.pack(anchor="w", padx=15, pady=(0, 8))

        # Verifica status do modelo ao abrir configurações
        self._check_model_status()

        # Separador visual
        sep = ctk.CTkFrame(self.scroll_container, height=1, fg_color="#374151")
        sep.pack(fill="x", padx=15, pady=(15, 10))

        # Botão Salvar
        save_btn = ctk.CTkButton(
            self.scroll_container,
            text="💾  Salvar Configurações",
            fg_color="#10b981",
            hover_color="#059669",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            height=42,
            command=self._save_settings
        )
        save_btn.pack(fill="x", padx=15, pady=(0, 20))

        # --- FOOTER COM CRÉDITOS ---
        footer_frame = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        footer_frame.pack(fill="x", pady=(15, 10))
        
        author_label = ctk.CTkLabel(
            footer_frame,
            text="Desenvolvido por: Carlos de Alcântara\ncarlosdealcantarajr@gmail.com",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color="#9ca3af"
        )
        author_label.pack(pady=(0, 0))

    def _check_model_status(self):
        """Verifica se o motor e o modelo existem e atualiza o label de status."""
        if not self.window or not self.window.winfo_exists():
            return
        try:
            engine_dir = os.path.join(CONFIG_DIR, "engine")
            model_file = os.path.join(CONFIG_DIR, "models", "ggml-small.bin")

            model_exists = os.path.isfile(model_file)
            engine_exists = (
                os.path.isdir(engine_dir) and
                any(f.lower().endswith('.exe') for f in os.listdir(engine_dir))
            )

            if model_exists and engine_exists:
                size_mb = os.path.getsize(model_file) // (1024 * 1024)
                self.model_status_label.configure(
                    text=f"✅ Motor de IA instalado ({size_mb} MB) — Pronto para uso!",
                    text_color="#10b981"
                )
                self.download_btn.configure(text="Reinstalar Componentes")
            elif model_exists:
                self.model_status_label.configure(
                    text="⚠️ Modelo encontrado, mas motor de IA ausente. Clique em Baixar.",
                    text_color="#fbbf24"
                )
                self.download_btn.configure(text="Baixar Motor de IA")
            else:
                self.model_status_label.configure(
                    text="❌ Modelo e motor de IA não encontrados. Clique em Baixar.",
                    text_color="#f87171"
                )
                self.download_btn.configure(text="Baixar Componentes de IA")
        except Exception as e:
            print(f"[Settings] Erro ao verificar status do modelo: {e}")

    def _start_download(self):
        """Dispara o script de download_resources.ps1 em background com progresso em tempo real."""
        import tempfile

        self.download_btn.configure(state="disabled", text="⏳ Iniciando...")
        self.model_status_label.configure(
            text="🔄 Preparando download...",
            text_color="#fbbf24"
        )

        # Arquivo temporário de progresso (comunicação PowerShell → Python)
        self._progress_file = os.path.join(tempfile.gettempdir(), "kw_download_progress.txt")
        try:
            with open(self._progress_file, "w", encoding="utf-8") as f:
                f.write("")
        except Exception:
            pass

        def download_thread():
            # Modelo sempre fixo: Small
            model_key = "small"

            # Localiza o script download_resources.ps1
            import sys
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            
            script_path = os.path.join(base_dir, "download_resources.ps1")
            
            # Localizações de fallback
            if not os.path.exists(script_path):
                script_path = r"C:\Program Files\KeyWhisper\download_resources.ps1"
            if not os.path.exists(script_path):
                script_path = r"C:\Program Files (x86)\KeyWhisper\download_resources.ps1"
            if not os.path.exists(script_path):
                script_path = os.path.join(CONFIG_DIR, "download_resources.ps1")

            try:
                cmd = [
                    "powershell.exe",
                    "-ExecutionPolicy", "Bypass",
                    "-WindowStyle", "Hidden",
                    "-NoProfile",
                    "-File", script_path,
                    "-SelectedModel", model_key,
                    "-ProgressFile", self._progress_file
                ]
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                proc.communicate()
                if self.window and self.window.winfo_exists():
                    self.window.after(0, lambda: self._on_download_finished(proc.returncode))
            except Exception as e:
                print(f"[Download] Erro ao disparar downloader: {e}")
                if self.window and self.window.winfo_exists():
                    self.window.after(0, lambda: self._on_download_finished(-1))

        threading.Thread(target=download_thread, daemon=True).start()
        # Inicia loop de polling do progresso
        self._poll_download_progress()

    def _poll_download_progress(self):
        """Lê o arquivo de progresso a cada 600ms e atualiza a UI em tempo real."""
        if not self.window or not self.window.winfo_exists():
            return
        try:
            progress_file = getattr(self, '_progress_file', None)
            if progress_file and os.path.exists(progress_file):
                with open(progress_file, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read().strip()
                if text:
                    if text.startswith("CONCLUIDO"):
                        return  # _on_download_finished vai tratar
                    elif text.startswith("ERRO:"):
                        self.model_status_label.configure(
                            text=f"❌ {text[5:].strip()}",
                            text_color="#f87171"
                        )
                        self.download_btn.configure(state="normal", text="Tentar Novamente")
                        return
                    else:
                        # Atualiza label com status atual
                        self.model_status_label.configure(
                            text=f"🔄 {text}",
                            text_color="#fbbf24"
                        )
                        # Atualiza o texto do botão com percentual se disponível
                        import re
                        pct_match = re.search(r'(\d+)%', text)
                        if pct_match:
                            pct = pct_match.group(1)
                            self.download_btn.configure(text=f"⏳ {pct}%")
        except Exception:
            pass
        # Agenda próxima checagem em 600ms
        self.window.after(600, self._poll_download_progress)

    def _on_download_finished(self, returncode):
        self.download_btn.configure(state="normal", text="Baixar Modelo")
        if returncode == 0:
            self._check_model_status()
        else:
            self.model_status_label.configure(
                text="❌ Falha no download. Verifique sua conexão ou logs em AppData.",
                text_color="#f87171"
            )

    def _save_settings(self):
        selected_lang_friendly = self.lang_menu.get()

        auto_startup_val = bool(self.startup_switch.get())

        new_config = {
            "file_path": self.config.get("file_path", DEFAULT_TRANSCRIPT),
            "hotkey": self.hotkey_entry.get().strip().lower(),
            "bridge_enabled": self.config.get("bridge_enabled", False),
            "show_welcome_on_startup": bool(self.welcome_switch.get()),
            "auto_startup": auto_startup_val,
            "model_name": "ggml-small.bin",
            "language": LANGUAGES.get(selected_lang_friendly, "pt"),
            "gpu_acceleration": True,
            "step_ms": 500,
            "length_ms": 5000
        }

        save_config(new_config)

        # Gerencia a chave de Registro do Windows para inicialização automática
        self._manage_windows_startup(auto_startup_val)
        
        if self.on_save_callback:
            self.on_save_callback(new_config)

        self.window.grab_release()
        self.window.destroy()
        self.window = None

    def _manage_windows_startup(self, enable):
        """Ativa ou desativa a inicialização automática do KeyWhisper via Registro do Windows."""
        import winreg
        import sys
        
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "KeyWhisper"
        
        # Resolve o caminho do executável (se compilado, usa o sys.executable, caso contrário o main.py não serve para o startup normal)
        if getattr(sys, 'frozen', False):
            exe_path = f'"{sys.executable}" --startup'
        else:
            # Em modo dev, não há sentido em adicionar ao startup, mas adicionamos para teste se necessário
            exe_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}" --startup'

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE | winreg.KEY_READ)
            if enable:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            print(f"[Settings] Erro ao gerenciar startup no registro: {e}")
