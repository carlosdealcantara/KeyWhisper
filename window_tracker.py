import time
import threading
import win32gui
import win32process
import os

def log_debug(message):
    log_dir = os.path.join(os.environ.get('APPDATA', ''), 'KeyWhisper')
    try:
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "debug_log.txt"), "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except Exception:
        pass

class WindowTracker:
    def __init__(self, check_interval=0.2):
        self.check_interval = check_interval
        self.last_target_hwnd = None
        self.running = False
        self.thread = None
        # Lista de nomes de classes ou títulos a serem ignorados
        self.ignored_titles = [
            "KeyWhisper", "WhisperDesktop", "StatusPopup", "Configurações", 
            "Capture Audio", "Whisper", "Desktop", "Debug Console", "Console de depuração",
            "Windows Input Experience", "Experiência de Entrada", "Ditado", "Dictation",
            "TextInputHost", "SearchHost", "StartHost", "ShellExperienceHost", "Cortana",
            "Task View", "Visão de Tarefas"
        ]
        self.ignored_classes = [
            "Shell_TrayWnd", "Shell_SecondaryTrayWnd", "WorkerW", "Progman",
            "DV2ControlHost", "Button", "Windows.UI.Core.CoreWindow",
            "EdgeUiInputTopWndClass"
        ]

    def _get_window_title(self, hwnd):
        try:
            return win32gui.GetWindowText(hwnd)
        except Exception:
            return ""

    def _should_ignore(self, hwnd):
        if not hwnd or not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
            return True
        
        # Verificar classe da janela
        try:
            class_name = win32gui.GetClassName(hwnd)
            if class_name in self.ignored_classes:
                return True
        except Exception:
            pass
            
        title = self._get_window_title(hwnd)
        # Ignorar janelas vazias ou de sistema comuns
        if not title or title in ["Program Manager", "Start", "Iniciar"]:
            return True

        # Ignorar janelas do próprio KeyWhisper ou do WhisperDesktop
        for ignored in self.ignored_titles:
            if ignored.lower() in title.lower():
                # Se contiver "keywhisper" ou "whisper", mas for o VS Code ou navegador, não ignore!
                if ignored.lower() in ["keywhisper", "whisper"] and any(x in title.lower() for x in ["visual studio code", "google chrome", "firefox", "edge"]):
                    continue
                return True
                
        return False

    def _track_loop(self):
        while self.running:
            try:
                hwnd = win32gui.GetForegroundWindow()
                if hwnd and not self._should_ignore(hwnd):
                    if hwnd != self.last_target_hwnd:
                        title = self._get_window_title(hwnd)
                        class_name = ""
                        try:
                            class_name = win32gui.GetClassName(hwnd)
                        except Exception:
                            pass
                        log_debug(f"[WindowTracker] Nova janela alvo detectada: HWND={hwnd}, Título='{title}', Classe='{class_name}'")
                        self.last_target_hwnd = hwnd
            except Exception as e:
                print(f"[WindowTracker] Erro ao rastrear janela: {e}")
            time.sleep(self.check_interval)

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._track_loop, daemon=True)
        self.thread.start()
        print("[WindowTracker] Rastreador de janelas iniciado.")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        print("[WindowTracker] Rastreador de janelas parado.")

    def get_target_window(self):
        """Retorna o handle da última janela ativa válida (onde o cursor deve estar)."""
        # Se a janela atual de foreground já for válida, retorna ela imediatamente
        try:
            current = win32gui.GetForegroundWindow()
            if current and not self._should_ignore(current):
                return current
        except Exception:
            pass
        return self.last_target_hwnd
