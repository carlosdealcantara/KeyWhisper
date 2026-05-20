import os
import sys
import time
import winsound
import threading
import customtkinter as ctk

from window_tracker import WindowTracker
from whisper_bridge import WhisperBridge
from text_injector import inject_text
from tray_icon import TrayIcon
from hotkey_manager import HotkeyManager
from ui_overlay import ToastNotification, ListeningPopup, WelcomeWindow
import settings

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
            print("[Core] Outra instância do KeyWhisper já está em execução. Encerrando esta.")
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

    # 1. Deduplicar repetição extrema de palavras consecutivas (ex: "Eita! Eita! Eita!...")
    words = text.split()
    if len(words) > 2:
        cleaned_words = []
        i = 0
        while i < len(words):
            word = words[i]
            clean_word = re.sub(r'[^\w]', '', word).lower()
            
            # Conta repetições consecutivas da mesma palavra
            count = 1
            while i + count < len(words):
                next_clean = re.sub(r'[^\w]', '', words[i + count]).lower()
                if clean_word and next_clean == clean_word:
                    count += 1
                else:
                    break
            
            # Limita a no máximo 2 repetições consecutivas da mesma palavra
            repetitions_to_keep = min(count, 2)
            for j in range(repetitions_to_keep):
                cleaned_words.append(words[i + j])
            
            i += count
        text = " ".join(cleaned_words)

    # 2. Deduplicar frases inteiras ou padrões de frases consecutivas (ex: "Aí. Aí.", ou padrões intercalados "A, B, A, B")
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) > 1:
        n = len(sentences)
        i = 0
        cleaned_sentences = []
        
        def clean_item(s):
            return re.sub(r'[^\w]', '', s).lower()
            
        clean_sentences = [clean_item(x) for x in sentences]
        
        while i < n:
            match_found = False
            # Testa padrões repetitivos de tamanho k (de 1 até 4 sentenças)
            for k in range(1, 5):
                if i + 2*k <= n:
                    pattern = clean_sentences[i : i+k]
                    # Desconsidera padrões vazios
                    if not any(pattern):
                        continue
                        
                    next_window = clean_sentences[i+k : i+2*k]
                    if pattern == next_window:
                        # Conta repetições consecutivas desse padrão
                        repeats = 1
                        while i + (repeats+1)*k <= n:
                            curr_window = clean_sentences[i + repeats*k : i + (repeats+1)*k]
                            if curr_window == pattern:
                                repeats += 1
                            else:
                                break
                        
                        # Adiciona o padrão uma única vez no resultado
                        cleaned_sentences.extend(sentences[i : i+k])
                        i += repeats * k
                        match_found = True
                        break
            if not match_found:
                cleaned_sentences.append(sentences[i])
                i += 1
        text = " ".join(cleaned_sentences)

    return text


class KeyWhisperApp:
    def __init__(self):
        # Janela invisível root do CustomTkinter para gerenciar o event loop e Toplevels
        self.root = ctk.CTk()
        self.root.withdraw() # Esconde a janela principal

        # Carrega as configurações locais
        self.config = settings.load_config()
        self.bridge_enabled = False # Inicia desligado/pausado por padrão, aguardando o F9
        self.popup = None

        # Inicializa o Toast flutuante
        self.toast = ToastNotification(self.root)

        # Histórico temporal para evitar redigitar alucinações consecutivas de silêncio (ex: "Obrigado!")
        self.last_injected_text = ""
        self.last_injected_time = 0.0
        self.last_active_time = 0.0

        # Inicializa o Rastreador de Janelas
        self.tracker = WindowTracker()
        self.tracker.start()

        # Inicializa a Ponte do WhisperDesktop (File Watcher)
        self.bridge = WhisperBridge(
            file_path=self.config.get("file_path", ""),
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

        # Se show_welcome_on_startup for True, exibe a WelcomeWindow na inicialização
        if self.config.get("show_welcome_on_startup", True):
            def on_welcome_close():
                if not self.config.get("file_path", ""):
                    print("[Core] Primeiro acesso detectado. Abrindo configurações...")
                    self.root.after(200, self.on_open_settings)
            
            welcome_win = WelcomeWindow(self.root, on_close_callback=on_welcome_close)
            self.root.after(100, welcome_win.show)
        elif not self.config.get("file_path", ""):
            print("[Core] Primeiro acesso detectado. Abrindo configurações...")
            self.root.after(800, self.on_open_settings)

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
        hallucinations = ["obrigado", "obrigado.", "obrigada", "obrigada.", "obrigado por assistir", "obrigado por assistir.", "obrigada por assistir"]
        
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
        """Callback acionado via atalho de teclado global (F9 por padrão)."""
        self.bridge_enabled = not self.bridge_enabled
        
        # Salva o novo estado nas configurações
        self.config["bridge_enabled"] = self.bridge_enabled
        settings.save_config(self.config)

        # Registra o tempo de desativação para o período de tolerância
        if self.bridge_enabled:
            self.last_active_time = float('inf')
        else:
            self.last_active_time = time.time()

        # Atualiza a bandeja
        self.tray.set_bridge_state(self.bridge_enabled)

        # Bipes e Pop-ups
        self.play_beep(self.bridge_enabled)
        self.update_popup_state()
        print(f"[Core] Ponte de injeção ligada/desligada via atalho. Estado atual: {self.bridge_enabled}")

    def on_tray_toggle(self, new_state):
        """Callback acionado ao clicar na opção de ativar/desativar no menu de clique direito do ícone tray."""
        self.bridge_enabled = new_state
        self.config["bridge_enabled"] = self.bridge_enabled
        settings.save_config(self.config)

        # Registra o tempo de desativação para o período de tolerância
        if self.bridge_enabled:
            self.last_active_time = float('inf')
        else:
            self.last_active_time = time.time()

        self.play_beep(self.bridge_enabled)
        self.update_popup_state()

    def update_popup_state(self):
        """Gerencia a criação e destruição da janela de popup flutuante de escuta."""
        if self.bridge_enabled:
            if not self.popup:
                def close_popup_cb():
                    self.root.after(0, self.on_toggle_bridge)
                self.popup = ListeningPopup(
                    parent_root=self.root,
                    on_close_callback=close_popup_cb,
                    on_settings_callback=self.on_open_settings
                )
            self.root.after(0, self.popup.show)
        else:
            if self.popup:
                p = self.popup
                self.popup = None
                p.close()

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
        old_file_path = self.config.get("file_path", "")

        self.config = new_config
        self.bridge_enabled = self.config.get("bridge_enabled", True)

        # 1. Atualiza a Ponte de Arquivo
        if old_file_path != self.config.get("file_path", ""):
            self.bridge.update_file_path(self.config.get("file_path", ""))
        
        if self.bridge_enabled:
            self.last_active_time = float('inf')
        else:
            self.last_active_time = time.time()

        # 2. Atualiza o Atalho de Teclado
        new_hotkey = self.config.get("hotkey", "f9")
        if old_hotkey != new_hotkey:
            self.hotkey_mgr.update_hotkey(new_hotkey, self.on_toggle_bridge)

        # 3. Atualiza o estado da bandeja
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

    def on_exit(self):
        """Finaliza todos os recursos e desliga o app de forma limpa."""
        print("[Core] Encerrando KeyWhisper...")
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

    app = KeyWhisperApp()
    app.run()
