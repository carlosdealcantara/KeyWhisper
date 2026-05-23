import os
import sys
import time
import winsound
import threading
import customtkinter as ctk

from window_tracker import WindowTracker
from whisper_bridge import WhisperBridge
from whisper_launcher import WhisperLauncher
from text_injector import inject_text
from tray_icon import TrayIcon
from hotkey_manager import HotkeyManager
from ui_overlay import ToastNotification, ListeningPopup, WelcomeWindow
import settings

# Caminho fixo v2.0 do arquivo de transcrição (dentro do APPDATA do usuário)
APPDATA_DIR = os.path.join(os.environ.get('APPDATA', ''), 'KeyWhisper')
DEFAULT_TRANSCRIPT = os.path.join(APPDATA_DIR, 'output', 'transcript.kwtmp')

# Configura um manipulador de exceção global para salvar em arquivo em caso de erro silencioso
def handle_exception(exc_type, exc_value, exc_traceback):
    import traceback
    log_dir = os.path.join(os.environ.get('APPDATA', ''), 'KeyWhisper')
    try:
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "error_log.txt"), "a", encoding="utf-8") as f:
            f.write(f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
    except Exception:
        pass
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = handle_exception

# Captura erros internos de callbacks do Tkinter de forma silenciosa e grava no log
def handle_tkinter_exception(self, exc, val, tb):
    import traceback
    log_dir = os.path.join(os.environ.get('APPDATA', ''), 'KeyWhisper')
    try:
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "error_log.txt"), "a", encoding="utf-8") as f:
            f.write(f"\n--- TKINTER CALLBACK ERROR {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            traceback.print_exception(exc, val, tb, file=f)
    except Exception:
        pass
    # Mantém a saída padrão no console se estiver rodando em desenvolvimento
    try:
        sys.__excepthook__(exc, val, tb)
    except Exception:
        pass

ctk.CTk.report_callback_exception = handle_tkinter_exception

# Mutex global para manter a referência ativa durante toda a vida do processo
_instance_mutex = None

def check_single_instance():
    global _instance_mutex
    try:
        import win32event
        import win32api
        import winerror
        
        # Cria o mutex nomeado global para a sessão atual
        _instance_mutex = win32event.CreateMutex(None, False, "Global\\KeyWhisper_SingleInstance_Mutex")
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            print("[Core] Outra instância do KeyWhisper já está em execução. Sinalizando e encerrando esta.")
            # Cria arquivo de sinal para que a instância ativa exiba a tela de boas-vindas
            try:
                signal_file = os.path.join(APPDATA_DIR, 'show_welcome.signal')
                os.makedirs(APPDATA_DIR, exist_ok=True)
                with open(signal_file, 'w') as f:
                    f.write('1')
            except Exception:
                pass
            sys.exit(0)
    except Exception as e:
        print(f"[Core] Erro ao inicializar instância única: {e}")

check_single_instance()

def log_debug(message):
    log_dir = os.path.join(os.environ.get('APPDATA', ''), 'KeyWhisper')
    try:
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "debug_log.txt"), "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except Exception:
        pass

def clean_whisper_repetitions(text):
    import re
    if not text:
        return text

    # Remove múltiplos espaços em branco
    text = re.sub(r'\s+', ' ', text).strip()
    words = text.split()
    
    # 1. Deduplicar padrões de palavras consecutivas (N-gramas de tamanho 1 a 4)
    # Ex: "eita eita eita" (k=1) ou "e o e o e o" (k=2) ou "e o que e o que" (k=3)
    i = 0
    cleaned_words = []
    n = len(words)
    
    while i < n:
        match_found = False
        # Testamos tamanhos de padrão k de 1 até 4 (crescente)
        for k in range(1, 5):
            if i + 2 * k <= n:
                pattern = words[i : i + k]
                # Normaliza para comparação sem caixa alta ou pontuação
                pattern_norm = [re.sub(r'[^\w]', '', w).lower() for w in pattern]
                
                # Ignora padrões que são compostos inteiramente por palavras vazias ou sem caracteres alfanuméricos
                if not any(pattern_norm):
                    continue
                
                # Conta quantas vezes esse padrão se repete consecutivamente a seguir
                repeats = 1
                while i + (repeats + 1) * k <= n:
                    next_window = words[i + repeats * k : i + (repeats + 1) * k]
                    next_window_norm = [re.sub(r'[^\w]', '', w).lower() for w in next_window]
                    if next_window_norm == pattern_norm:
                        repeats += 1
                    else:
                        break
                
                if repeats > 2:
                    # Se houver mais de 2 repetições consecutivas do padrão,
                    # mantemos apenas 2 ocorrências dele e pulamos as demais
                    cleaned_words.extend(words[i : i + 2 * k])
                    i += repeats * k
                    match_found = True
                    break
                elif repeats == 2:
                    # Se houver exatamente 2, mantemos ambas e avançamos
                    cleaned_words.extend(words[i : i + 2 * k])
                    i += 2 * k
                    match_found = True
                    break
        
        if not match_found:
            cleaned_words.append(words[i])
            i += 1
            
    text = " ".join(cleaned_words)

    # 2. Deduplicar frases inteiras ou sentenças consecutivas separadas por pontuação (ex: "Aí. Aí.")
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) > 1:
        n_s = len(sentences)
        i = 0
        cleaned_sentences = []
        
        def clean_item(s):
            return re.sub(r'[^\w]', '', s).lower()
            
        clean_sentences = [clean_item(x) for x in sentences]
        
        while i < n_s:
            match_found = False
            for k in range(1, 5):
                if i + 2*k <= n_s:
                    pattern = clean_sentences[i : i+k]
                    if not any(pattern):
                        continue
                        
                    next_window = clean_sentences[i+k : i+2*k]
                    if pattern == next_window:
                        repeats = 1
                        while i + (repeats+1)*k <= n_s:
                            curr_window = clean_sentences[i + repeats*k : i + (repeats+1)*k]
                            if curr_window == pattern:
                                repeats += 1
                            else:
                                break
                        
                        # Limita a repetição de sentenças inteiras a no máximo 1 ocorrência
                        cleaned_sentences.extend(sentences[i : i+k])
                        i += repeats * k
                        match_found = True
                        break
            if not match_found:
                cleaned_sentences.append(sentences[i])
                i += 1
        text = " ".join(cleaned_sentences)

    return text


def _register_dummy_extension():
    """Registra uma extensão dummy no registro do Windows para evitar pop-ups do WhisperDesktop"""
    try:
        import winreg
        ext = ".kwtmp"
        prog_id = "KeyWhisper.DummyFile"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{ext}") as key:
            winreg.SetValue(key, "", winreg.REG_SZ, prog_id)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{prog_id}\shell\open\command") as key:
            winreg.SetValue(key, "", winreg.REG_SZ, 'rundll32.exe')
    except Exception as e:
        log_debug(f"[Core] Erro ao registrar extensão dummy: {e}")

class KeyWhisperApp:
    def __init__(self, silent=False):
        # Janela invisível root do CustomTkinter para gerenciar o event loop e Toplevels
        self.root = ctk.CTk()
        self.root.withdraw() # Esconde a janela principal

        # Carrega as configurações locais
        self.config = settings.load_config()
        self.bridge_enabled = False # Inicia desligado/pausado por padrão, aguardando o F9
        self.session_active = False # Controla se o popup flutuante está na tela
        self.config["bridge_enabled"] = False  # Garante que config em disco também reflita o estado desligado
        settings.save_config(self.config)
        self.popup = None

        # Inicializa o Toast flutuante
        self.toast = ToastNotification(self.root)

        # Histórico temporal para evitar redigitar alucinações consecutivas de silêncio (ex: "Obrigado!")
        self.last_injected_text = ""
        self.last_injected_time = 0.0
        self.last_active_time = 0.0

        # v2.0: Garante que o file_path aponte para o transcript fixo do motor headless
        if self.config.get("file_path", "") != DEFAULT_TRANSCRIPT:
            self.config["file_path"] = DEFAULT_TRANSCRIPT
            settings.save_config(self.config)

        # Registra a extensão dummy para silenciar o ShellExecute
        _register_dummy_extension()

        # Inicializa o Rastreador de Janelas
        self.tracker = WindowTracker()
        self.tracker.start()

        # v2.0: Inicializa e inicia o motor de transcrição headless (WhisperLauncher)
        self.launcher = WhisperLauncher()
        self.launcher.set_capture_state(self.bridge_enabled)
        launcher_started = self.launcher.start()
        if not launcher_started:
            log_debug("[Core] Motor headless não pôde ser iniciado. Agendando verificação de setup...")
            self.root.after(2000, self._check_setup_errors)

        # Inicializa a Ponte de Arquivo (File Watcher) apontando para o transcript fixo v2.0
        self.bridge = WhisperBridge(
            file_path=self.config.get("file_path", DEFAULT_TRANSCRIPT),
            on_text_received=self.on_text_received
        )
        self.bridge.start()  # Mantém a ponte sempre ativa para capturar transcrições pós-desativação

        # Inicializa o Atalho Global do Teclado
        self.hotkey_mgr = HotkeyManager(hotkey=self.config.get("hotkey", "f9"))
        self.hotkey_mgr.setup(callback=self.on_toggle_bridge)

        # Inicializa o Atalho Global para abrir as Configurações (Ctrl+Shift+F9)
        self.hotkey_mgr_settings = HotkeyManager(hotkey="ctrl+shift+f9")
        self.hotkey_mgr_settings.setup(callback=self.on_open_settings)

        # Inicializa o Ícone da Bandeja (Tray Icon) com delay para evitar conflitos
        self.tray = TrayIcon()
        self.root.after(1000, lambda: self.tray.setup(
            settings_cb=self.on_open_settings,
            exit_cb=self.on_exit
        ))

        print("[Core] KeyWhisper v2.0 inicializado com sucesso.")

        if not silent:
            # Se show_welcome_on_startup for True, exibe a WelcomeWindow na inicialização
            if self.config.get("show_welcome_on_startup", True):
                welcome_win = WelcomeWindow(self.root, on_close_callback=None)
                # Atrasa 1.5 segundos (1500ms) para escapar da guerra de foco do carregamento do motor
                self.root.after(1500, welcome_win.show)
                # Abre o popup junto para mostrar como funciona
                def show_popup_with_welcome():
                    if not self.session_active:
                        self.on_toggle_bridge()
                self.root.after(1500, show_popup_with_welcome)
            else:
                hotkey_name = self.config.get("hotkey", "F9").upper()
                self.root.after(1500, lambda: self.toast.show(f"✅ KeyWhisper Ativo!\nPressione {hotkey_name} para ditar", duration_ms=4000))
        else:
            log_debug("[Core] Inicializado em modo SILENCIOSO (Startup). Nenhuma interface será exibida.")

        # Monitor de sinal: se o usuário tentar abrir o KW novamente, exibe a tela de boas-vindas
        self._start_signal_monitor()

    def play_beep(self, active=True):
        """Toca um bip sonoro amigável do Windows em thread para não travar a execução."""
        def beep_thread():
            try:
                import os
                if active:
                    sound_path = r"C:\Windows\Media\Speech On.wav"
                    if os.path.exists(sound_path):
                        winsound.PlaySound(sound_path, winsound.SND_FILENAME)
                    else:
                        winsound.Beep(900, 120)
                else:
                    sound_path = r"C:\Windows\Media\Speech Off.wav"
                    if os.path.exists(sound_path):
                        winsound.PlaySound(sound_path, winsound.SND_FILENAME)
                    else:
                        winsound.Beep(700, 120)
            except Exception:
                pass
        threading.Thread(target=beep_thread, daemon=True).start()

    def on_text_received(self, text):
        """Callback acionado quando o WhisperBridge detecta nova transcrição escrita no arquivo."""
        # Permite injeção se ativo OU se estiver dentro de um intervalo de tolerância de 5 segundos após desativação
        if not self.bridge_enabled and (time.time() - self.last_active_time) >= 5.0:
            log_debug("[Core] Texto recebido ignorado: ponte está pausada e período de tolerância expirou.")
            return

        log_debug(f"[Core] Texto bruto recebido do WhisperBridge: '{text}'")

        # Filtra alucinações e anotações do Whisper
        # Remove colchetes como [falando do vídeo], [som de descarregamento de água]
        import re
        cleaned_text = re.sub(r'\[.*?\]', '', text)
        
        # Remove anotações entre parênteses como (risos), (som de vento)
        noise_keywords = ['som', 'ruído', 'risos', 'tosse', 'música', 'falando', 'telefone', 'vento', 'vídeo', 'background', 'silêncio']
        def replace_parentheses(match):
            content = match.group(1).lower()
            if any(keyword in content for keyword in noise_keywords):
                return ""
            return match.group(0)
        cleaned_text = re.sub(r'\((.*?)\)', replace_parentheses, cleaned_text)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

        # Limpa repetições e loops de alucinação do Whisper
        cleaned_text = clean_whisper_repetitions(cleaned_text)

        if not cleaned_text:
            log_debug(f"[Core] Texto recebido '{text}' foi identificado como ruído ou alucinação do Whisper e foi filtrado com sucesso.")
            return

        # Filtro temporal contra alucinações de silêncio recorrentes e lista negra
        current_time = time.time()
        
        # Lista de alucinações comuns do Whisper em português quando há silêncio
        hallucinations = [
            "obrigado", "obrigado.", "obrigada", "obrigada.", 
            "obrigado por assistir", "obrigado por assistir.", "obrigada por assistir",
            "e", "e.", "o", "o.", "a", "a.", "e o", "e a", "m", "m.", "um", "um.", "uma", "uma."
        ]
        
        is_hallucination = False
        lower_cleaned = cleaned_text.lower().strip()
        
        if lower_cleaned in hallucinations:
            is_hallucination = True
        elif (lower_cleaned == self.last_injected_text.lower() and 
              (current_time - self.last_injected_time) < 10.0 and 
              len(cleaned_text.split()) <= 2):
            is_hallucination = True

        if is_hallucination:
            log_debug(f"[Core] Texto '{cleaned_text}' foi identificado como alucinação de silêncio e foi filtrado com sucesso.")
            return

        self.last_injected_text = cleaned_text
        self.last_injected_time = current_time

        text = cleaned_text
        log_debug(f"[Core] Texto filtrado com sucesso: '{text}'")

        # Busca a última janela onde o usuário estava digitando
        target_hwnd = self.tracker.get_target_window()
        if not target_hwnd:
            log_msg = "[Core] AVISO: Nenhuma janela ativa válida capturada pelo tracker para injetar texto!"
            print(log_msg)
            log_debug(log_msg)
            
            # Avisa o usuário via Toast e som de alerta de que ele precisa selecionar o campo de texto
            self.play_beep(active=False)
            if self.config.get("toast_enabled", True):
                self.root.after(0, lambda: self.toast.show("⚠️ Clique no campo de texto!", duration_ms=2500))
            return

        log_debug(f"[Core] Janela alvo válida encontrada: HWND={target_hwnd}. Agendando injeção...")

        # Garante que a injeção rode de forma thread-safe na thread principal
        def run_injection():
            log_debug(f"[Core] Iniciando injeção na janela HWND={target_hwnd}")
            inject_text(text, target_hwnd)
            log_debug("[Core] Injeção concluída com sucesso.")

        self.root.after(0, run_injection)

    def on_toggle_bridge(self):
        """Callback acionado via atalho de teclado global (F9 por padrão). Controla a SESSÃO (abre/fecha popup)."""
        if not self.launcher.is_running_normally():
            log_debug("[Core] F9 pressionado mas o motor não está rodando normalmente. Mostrando diálogo de recuperação...")
            self.play_beep(active=False)
            self._show_setup_recovery_dialog()
            return

        if not self.session_active:
            # Inicia a sessão (abre popup e liga escuta)
            self.session_active = True
            self.bridge_enabled = True
        else:
            # Encerra a sessão sempre, independentemente de estar pausado ou não
            self.session_active = False
            self.bridge_enabled = False
        
        self.config["bridge_enabled"] = self.bridge_enabled
        settings.save_config(self.config)
        self.launcher.set_capture_state(self.bridge_enabled)

        if self.bridge_enabled:
            self.last_active_time = float('inf')
        else:
            self.last_active_time = time.time()

        self.tray.set_bridge_state(self.bridge_enabled)
        self.play_beep(self.bridge_enabled)
        self.update_popup_state()
        print(f"[Core] F9 acionado. Sessão: {self.session_active}, Escuta: {self.bridge_enabled}")

    def on_tray_toggle(self, new_state):
        """Callback acionado ao clicar na opção de ativar/desativar no menu de clique direito do ícone tray."""
        self.bridge_enabled = new_state
        self.config["bridge_enabled"] = self.bridge_enabled
        settings.save_config(self.config)

        # Sincroniza o Capture do WhisperDesktop com o estado do F9
        self.launcher.set_capture_state(self.bridge_enabled)

        # Registra o tempo de desativação para o período de tolerância
        if self.bridge_enabled:
            self.last_active_time = float('inf')
        else:
            self.last_active_time = time.time()

        self.play_beep(self.bridge_enabled)
        self.update_popup_state()

    def on_toggle_pause_callback(self):
        """Acionado ao clicar no botão de microfone do popup (PAUSA). Altera apenas o estado da escuta."""
        self.bridge_enabled = not self.bridge_enabled
        self.config["bridge_enabled"] = self.bridge_enabled
        settings.save_config(self.config)
        self.launcher.set_capture_state(self.bridge_enabled)
        self.tray.set_bridge_state(self.bridge_enabled)
        
        if self.bridge_enabled:
            self.last_active_time = float('inf')
        else:
            self.last_active_time = time.time()
            
        self.play_beep(self.bridge_enabled)
        
        if self.popup:
            self.popup.set_paused(not self.bridge_enabled)

    def update_popup_state(self):
        """Gerencia a criação e destruição da janela de popup flutuante baseado na sessão ativa."""
        if self.session_active:
            if not self.popup:
                def close_popup_cb():
                    self.root.after(0, self.on_toggle_bridge)
                def toggle_pause_cb():
                    self.root.after(0, self.on_toggle_pause_callback)
                self.popup = ListeningPopup(
                    parent_root=self.root,
                    on_close_callback=close_popup_cb,
                    on_settings_callback=self.on_open_settings,
                    on_toggle_pause_callback=toggle_pause_cb
                )
                self.popup.show()
                # Atualiza para pausado se o bridge não estiver ativo ao criar o popup
                self.popup.set_paused(not self.bridge_enabled)
            else:
                self.popup.set_paused(not self.bridge_enabled)
        else:
            if self.popup:
                self.popup.close()
                self.popup = None

    def on_open_settings(self):
        """Abre a tela de configurações em customtkinter."""
        self.root.after(0, self._create_settings_window)

    def _create_settings_window(self):
        settings_win = settings.SettingsWindow(
            parent_root=self.root,
            on_save_callback=self.on_settings_saved
        )
        settings_win.show()

    def on_settings_saved(self, new_config):
        """Callback acionado após o usuário salvar novas preferências no painel."""
        print("[Core] Novas configurações aplicadas.")
        old_hotkey = self.config.get("hotkey", "f9")
        old_model = self.config.get("model_name", "")
        old_language = self.config.get("language", "")
        old_gpu = self.config.get("gpu_acceleration", True)

        self.config = new_config
        self.bridge_enabled = self.config.get("bridge_enabled", True)

        # 1. Ponte de Arquivo: sempre aponta para o transcript fixo do motor v2.0
        transcript_path = self.config.get("file_path", DEFAULT_TRANSCRIPT)
        self.bridge.update_file_path(transcript_path)
        
        if self.bridge_enabled:
            self.last_active_time = float('inf')
        else:
            self.last_active_time = time.time()

        # 2. Atualiza o Atalho de Teclado se mudou
        new_hotkey = self.config.get("hotkey", "f9")
        if old_hotkey != new_hotkey:
            self.hotkey_mgr.update_hotkey(new_hotkey, self.on_toggle_bridge)

        # 3. Reinicia o motor headless se as configurações de IA mudaram
        new_model = self.config.get("model_name", "")
        new_language = self.config.get("language", "")
        new_gpu = self.config.get("gpu_acceleration", True)
        ai_settings_changed = (old_model != new_model or old_language != new_language or old_gpu != new_gpu)
        if ai_settings_changed:
            log_debug("[Core] Configurações de IA alteradas — reiniciando motor headless...")
            def restart_engine():
                self.launcher.stop()
                time.sleep(1)
                self.launcher.start()
            threading.Thread(target=restart_engine, daemon=True).start()

        # 4. Atualiza o estado da bandeja
        self.tray.set_bridge_state(self.bridge_enabled)
        
        self.root.after(0, lambda: self.toast.show("⚙️ Configurações Salvas!", duration_ms=1200))

    def on_test_file(self):
        """Abre o arquivo monitorado para teste rápido."""
        path = self.config.get("file_path", "")
        if not path:
            self.root.after(0, lambda: self.toast.show("⚠️ Configure o arquivo primeiro!", duration_ms=1500))
            return
        
        if not os.path.exists(path):
            try:
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write("")
            except Exception:
                pass

        try:
            os.startfile(path)
        except Exception as e:
            print(f"[Core] Erro ao abrir arquivo para teste: {e}")

    def _start_signal_monitor(self):
        """Verifica periodicamente se uma segunda instância sinalizou para exibir a tela de boas-vindas."""
        signal_file = os.path.join(APPDATA_DIR, 'show_welcome.signal')
        try:
            if os.path.exists(signal_file):
                os.remove(signal_file)
                log_debug("[Core] Sinal de segunda instância detectado. Exibindo tela de boas-vindas.")
                welcome_win = WelcomeWindow(self.root, on_close_callback=None)
                self.root.after(100, welcome_win.show)
                def show_popup_with_welcome2():
                    if not self.session_active:
                        self.on_toggle_bridge()
                self.root.after(100, show_popup_with_welcome2)
        except Exception:
            pass
        # Reagenda a verificação a cada 1 segundo
        self.root.after(1000, self._start_signal_monitor)

    def _check_setup_errors(self):
        """Verifica se houve falha na instalação e oferece recuperação ao usuário."""
        error_log = os.path.join(APPDATA_DIR, 'setup_error.txt')
        engine_failed = os.path.exists(error_log) or not self.launcher.is_ready()
        
        if engine_failed:
            log_debug("[Core] Detectado motor/modelo ausente ou falha no setup. Exibindo diálogo de recuperação.")
            self._show_setup_recovery_dialog()

    def _show_setup_recovery_dialog(self):
        """Exibe um diálogo elegante para recuperar componentes de IA ausentes."""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("KeyWhisper — Configuração Necessária")
        dialog.geometry("480x240")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)  # Garante que fique no topo absoluto
        dialog.grab_set()
        dialog.focus()

        # Centraliza na tela
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 240
        y = (dialog.winfo_screenheight() // 2) - 120
        dialog.geometry(f"480x240+{x}+{y}")

        ctk.CTkLabel(
            dialog,
            text="⚠️  Componentes de IA Ausentes",
            font=ctk.CTkFont(family="Inter", size=17, weight="bold"),
            text_color=("#d97706", "#fbbf24")  # Laranja escuro no claro, amarelo no escuro
        ).pack(pady=(25, 10))

        ctk.CTkLabel(
            dialog,
            text="O motor de transcrição ou o modelo de IA não foram encontrados.\nIsso pode ter ocorrido por falha de conexão durante a instalação.\nAbra as Configurações para baixá-los agora.",
            font=ctk.CTkFont(family="Inter", size=12),
            text_color=("gray10", "gray90"),  # Preto no claro, branco/cinza claro no escuro
            justify="center",
            wraplength=420
        ).pack(pady=(0, 20))

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30)

        ctk.CTkButton(
            btn_frame,
            text="Abrir Configurações",
            fg_color="#10b981",
            hover_color="#059669",
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            command=lambda: [dialog.destroy(), self.on_open_settings()]
        ).pack(side="right")

        ctk.CTkButton(
            btn_frame,
            text="Ignorar por Agora",
            fg_color="#374151",
            hover_color="#4b5563",
            font=ctk.CTkFont(family="Inter", size=13),
            command=dialog.destroy
        ).pack(side="left")

    def on_exit(self):
        """Finaliza todos os recursos e desliga o app de forma limpa."""
        print("[Core] Encerrando KeyWhisper...")
        self.launcher.stop()
        self.tracker.stop()
        self.bridge.stop()
        self.hotkey_mgr.cleanup()
        self.hotkey_mgr_settings.cleanup()
        self.tray.stop()
        self.root.quit()
        self.root.destroy()
        sys.exit(0)

    def run(self):
        # Mantém o event loop do CustomTkinter ativo em background
        self.root.mainloop()

if __name__ == "__main__":
    # Garante suporte a alta DPI no Windows para fontes nítidas
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    is_startup_mode = "--startup" in sys.argv

    app = KeyWhisperApp(silent=is_startup_mode)
    app.run()
