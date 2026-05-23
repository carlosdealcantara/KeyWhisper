"""
whisper_launcher.py
Gerencia a execução invisível do motor de transcrição do KeyWhisper (v2.0).
Suporta whisper-stream.exe (via stdout) e WhisperDesktop.exe (via registro e execução oculta).
"""
import os
import sys
import subprocess
import threading
import time
import json
import re

# Constantes de Diretório
APPDATA_DIR = os.path.join(os.environ.get('APPDATA', ''), 'KeyWhisper')
ENGINE_DIR = os.path.join(APPDATA_DIR, 'engine')
MODELS_DIR = os.path.join(APPDATA_DIR, 'models')
OUTPUT_DIR = os.path.join(APPDATA_DIR, 'output')
TRANSCRIPT_FILE = os.path.join(OUTPUT_DIR, 'transcript.kwtmp')

def log_debug(message):
    try:
        os.makedirs(APPDATA_DIR, exist_ok=True)
        with open(os.path.join(APPDATA_DIR, "debug_log.txt"), "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Launcher] {message}\n")
    except Exception:
        pass

def compute_language_dword(lang_code):
    """Gera o DWORD little-endian ASCII para o registro do WhisperDesktop (ex: 'pt' -> 29808)."""
    if not lang_code or lang_code == "auto":
        return 0
    if len(lang_code) >= 2:
        return ord(lang_code[0]) + (ord(lang_code[1]) * 256)
    return 0

class WhisperLauncher:
    def __init__(self):
        self._process = None
        self._monitor_thread = None
        self._running = False
        self._engine_type = None # 'stream' ou 'desktop'
        self.last_launch_time = 0.0
        self._whisper_hwnd = None
        self._desired_capture_state = None
        self._last_state_change_time = 0.0

        # Inicia a thread sentinela imortal (leve)
        threading.Thread(target=self._window_sentinel, daemon=True).start()

    def _window_sentinel(self):
        """Thread contínua e super leve que roda durante TODA a vida do KeyWhisper,
        escondendo as janelas rebeldes do WhisperDesktop mesmo que o gerenciador principal falhe."""
        try:
            import win32gui
            import win32con
        except ImportError:
            return

        while True:
            try:
                for title in ("Capture Audio", "WhisperDesktop", "Load Whisper Model"):
                    hwnd = win32gui.FindWindow(None, title)
                    if hwnd and hwnd != 0:
                        if win32gui.IsWindowVisible(hwnd):
                            win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
                            log_debug(f"[Sentinela] Janela '{title}' abatida e ocultada!")
                        rect = win32gui.GetWindowRect(hwnd)
                        if rect[0] != -32000 or rect[1] != -32000:
                            win32gui.SetWindowPos(
                                hwnd, 0, -32000, -32000, 0, 0,
                                win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE
                            )
            except Exception:
                pass
            
            # Executa a cada 100ms (10 vezes por segundo) - impacto zero na CPU
            time.sleep(0.1)

    def get_paths(self):
        config_path = os.path.join(APPDATA_DIR, 'config.json')
        model_name = "ggml-small.bin"
        language = "pt"
        gpu_acc = True
        step_ms = 500
        length_ms = 5000

        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8-sig") as f:
                    cfg = json.load(f)
                    model_name = cfg.get("model_name", model_name)
                    language = cfg.get("language", language)
                    gpu_acc = cfg.get("gpu_acceleration", gpu_acc)
                    step_ms = cfg.get("step_ms", step_ms)
                    length_ms = cfg.get("length_ms", length_ms)
            except Exception as e:
                log_debug(f"Erro ao ler config.json: {e}")

        model_path = os.path.normpath(os.path.join(MODELS_DIR, model_name))
        return model_path, language, gpu_acc, step_ms, length_ms

    def detect_engine(self):
        """Detecta qual executável de motor está disponível na pasta."""
        stream_path = os.path.join(ENGINE_DIR, 'whisper-stream.exe')
        desktop_path = os.path.join(ENGINE_DIR, 'WhisperDesktop.exe')
        
        if os.path.isfile(stream_path):
            self._engine_type = 'stream'
            return stream_path
        elif os.path.isfile(desktop_path):
            self._engine_type = 'desktop'
            return desktop_path
        
        # Procura por qualquer executável na pasta engine caso mude de nome
        if os.path.exists(ENGINE_DIR):
            for file in os.listdir(ENGINE_DIR):
                if file.lower().endswith('.exe'):
                    if 'desktop' in file.lower():
                        self._engine_type = 'desktop'
                    else:
                        self._engine_type = 'stream'
                    return os.path.join(ENGINE_DIR, file)
        
        self._engine_type = None
        return None

    def is_ready(self) -> bool:
        model_path, _, _, _, _ = self.get_paths()
        engine_exe = self.detect_engine()
        model_exists = os.path.isfile(model_path)
        
        ready = (engine_exe is not None) and model_exists
        log_debug(f"Pronto para rodar? {ready} (Engine: {engine_exe}, Modelo: {model_path})")
        return ready

    def is_running_normally(self) -> bool:
        """Verifica se o motor está ativo e rodando sem erros."""
        if not self.is_ready():
            return False
        if not self._running:
            return False
        if self._process is None or self._process.poll() is not None:
            return False
        return True

    def start(self) -> bool:
        if self._running:
            return True
            
        if not self.is_ready():
            log_debug("Motor ou modelo ausente. Não é possível iniciar.")
            return False

        # Encerra preventivamente processos órfãos que possam estar rodando
        try:
            # 1. Tenta usar taskkill nativo
            subprocess.run(["taskkill", "/F", "/IM", "WhisperDesktop.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
            subprocess.run(["taskkill", "/F", "/IM", "whisper-stream.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
            
            # 2. Varredura agressiva via psutil (para contornar falhas de permissão no taskkill)
            try:
                import psutil
                for p in psutil.process_iter(['name']):
                    if p.info['name'] and p.info['name'].lower() in ('whisperdesktop.exe', 'whisper-stream.exe'):
                        try:
                            p.kill()
                            log_debug(f"Processo órfão aniquilado via psutil: {p.info['name']} (PID: {p.pid})")
                        except Exception:
                            pass
            except ImportError:
                pass

            log_debug("Limpeza de instâncias órfãs concluída.")
            import time
            time.sleep(1.5) # Dá tempo para o SO limpar os processos e o mutex ser liberado
        except Exception as e:
            log_debug(f"Erro ao encerrar processos antigos: {e}")
        
        # Garante a existência do arquivo de transcrição vazio
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        try:
            with open(TRANSCRIPT_FILE, "w", encoding="utf-8") as f:
                f.write("")
        except Exception as e:
            log_debug(f"Erro ao limpar transcript.txt: {e}")

        self._running = True
        
        # Configura registro se o motor for WhisperDesktop.exe
        engine_exe = self.detect_engine()
        if self._engine_type == 'desktop':
            self._setup_whisper_desktop_registry()

        self._launch(engine_exe)
        
        self._monitor_thread = threading.Thread(target=self._monitor, daemon=True)
        self._monitor_thread.start()
        return True

    def _setup_whisper_desktop_registry(self):
        """Escreve as configurações no Registro do Windows para o WhisperDesktop."""
        try:
            import winreg
            model_path, language, gpu_acc, _, _ = self.get_paths()
            
            key_path = r"Software\const.me\WhisperDesktop"
            # Abre ou cria a chave de registro do WhisperDesktop
            key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            
            # Grava os valores exigidos
            winreg.SetValueEx(key, "modelPath", 0, winreg.REG_SZ, model_path)
            winreg.SetValueEx(key, "modelImpl", 0, winreg.REG_SZ, "GPU" if gpu_acc else "CPU")
            winreg.SetValueEx(key, "language", 0, winreg.REG_DWORD, compute_language_dword(language))
            winreg.SetValueEx(key, "captureTextFile", 0, winreg.REG_SZ, TRANSCRIPT_FILE)
            winreg.SetValueEx(key, "captureTextFlags", 0, winreg.REG_DWORD, 1) # Apenas escrever em arquivo (sem abrir Notepad ao parar)
            
            winreg.CloseKey(key)
            log_debug("Registro do WhisperDesktop pré-populado com sucesso.")
        except Exception as e:
            log_debug(f"Erro ao configurar registro do WhisperDesktop: {e}")

    def _launch(self, engine_exe):
        self.last_launch_time = time.time()
        model_path, language, gpu_acc, step_ms, length_ms = self.get_paths()
        
        # Ocultação absoluta no Windows
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0 # SW_HIDE (Janela oculta)
        
        if self._engine_type == 'stream':
            # Parametros para whisper-stream.exe
            args = [
                engine_exe,
                "-m", model_path,
                "-l", language,
                "--step", str(step_ms),
                "--length", str(length_ms),
                "-t", "4",
            ]
            if gpu_acc:
                args.append("--gpu-d3d11") # Se habilitado
                
            log_debug(f"Iniciando whisper-stream: {' '.join(args)}")
            try:
                self._process = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                # Thread dedicada para capturar o stdout e gravar no transcript.txt
                if self._engine_type == 'stream':
                    threading.Thread(target=self._capture_output, daemon=True).start()
            except Exception as e:
                log_debug(f"Falha ao iniciar whisper-stream: {e}")
                
        elif self._engine_type == 'desktop':
            # WhisperDesktop.exe é controlado por registro e GUI oculta
            log_debug(f"Iniciando WhisperDesktop invisível: {engine_exe}")
            
            # Posiciona a janela fora da tela desde a criação para evitar qualquer flicker/piscar
            startupinfo.dwFlags |= 0x04  # STARTF_USEPOSITION
            startupinfo.dwX = -32000
            startupinfo.dwY = -32000
            
            try:
                self._process = subprocess.Popen(
                    [engine_exe],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                # Thread dedicada para gerenciar a ocultação da janela e manter o Capture ativo
                threading.Thread(target=self._manage_whisper_desktop_gui, args=(self._process.pid,), daemon=True).start()
            except Exception as e:
                log_debug(f"Falha ao iniciar WhisperDesktop: {e}")

    def _capture_output(self):
        """Lê o stdout do whisper-stream em tempo real e alimenta o transcript.txt."""
        if not self._process or not self._process.stdout:
            return
            
        log_debug("Thread de captura de stdout ativa.")
        for line in iter(self._process.stdout.readline, b''):
            if not self._running:
                break
            try:
                text = line.decode('utf-8', errors='ignore').strip()
                if text:
                    # Limpa marcações de timestamp como [00:00.000 --> 00:02.000] se houverem
                    clean_text = re.sub(r'\[\d{2}:\d{2}\.\d{3}\s+-->\s+\d{2}:\d{2}\.\d{3}\]', '', text).strip()
                    if clean_text:
                        with open(TRANSCRIPT_FILE, "a", encoding="utf-8") as f:
                            f.write(clean_text + "\n")
            except Exception as e:
                log_debug(f"Erro ao capturar linha: {e}")

    def _monitor(self):
        """Monitora se o processo do motor caiu inesperadamente e reinicia se necessário."""
        consecutive_failures = 0
        max_consecutive_failures = 3
        
        while self._running:
            if self._process:
                poll_res = self._process.poll()
                if poll_res is not None:
                    consecutive_failures += 1
                    log_debug(f"Motor caiu de forma inesperada (Código de saída: {poll_res}). Falha consecutiva {consecutive_failures}/{max_consecutive_failures}.")
                    
                    if consecutive_failures >= max_consecutive_failures:
                        log_debug("Número máximo de falhas consecutivas atingido. Desativando monitor para evitar loop infinito.")
                        self._running = False
                        self._process = None
                        
                        try:
                            error_log = os.path.join(APPDATA_DIR, 'setup_error.txt')
                            with open(error_log, "w", encoding="utf-8") as ef:
                                ef.write("O motor de transcrição falhou repetidamente ao iniciar.\nIsso pode ser causado por um modelo corrompido ou incompatibilidade da aceleração de GPU.")
                        except Exception:
                            pass
                        break
                        
                    log_debug("Tentando reiniciar em 3 segundos...")
                    time.sleep(3)
                    if self._running:
                        engine_exe = self.detect_engine()
                        if engine_exe:
                            if self._engine_type == 'desktop':
                                self._setup_whisper_desktop_registry()
                            self._launch(engine_exe)
                else:
                    if time.time() - self.last_launch_time > 20:
                        if consecutive_failures > 0:
                            log_debug("Motor rodando estável. Resetando contador de falhas consecutivas.")
                            consecutive_failures = 0
            time.sleep(2)

    def _manage_whisper_desktop_gui(self, pid):
        """Monitora o WhisperDesktop para ocultar todas as suas janelas e manter a referência do HWND operacional ativa."""
        try:
            import win32gui
            import win32process
            import win32con
        except ImportError:
            log_debug("Bibliotecas win32gui/win32process/win32con não disponíveis. Monitoramento desativado.")
            return

        log_debug(f"Gerenciador da GUI do WhisperDesktop iniciado para o PID {pid}...")
        start_time = time.time()

        # Loop contínuo enquanto o processo estiver rodando e a aplicação ativa
        while self._running and self._process and self._process.poll() is None:
            try:
                # 1. Abordagem direta: busca imediata por título conhecido (sem enumerar por PID)
                #    Isso garante ocultamento mesmo quando a janela aparece tardiamente (após carregar modelo)
                for known_title in ("Capture Audio", "WhisperDesktop"):
                    try:
                        dh = win32gui.FindWindow(None, known_title)
                        if dh and dh != 0:
                            # Oculta independentemente do PID (garante que janelas órfãs sejam alvejadas)
                            if win32gui.IsWindowVisible(dh):
                                win32gui.ShowWindow(dh, win32con.SW_HIDE)
                                log_debug(f"[FindWindow] Janela '{known_title}' agressivamente ocultada: HWND={dh}")
                            rect = win32gui.GetWindowRect(dh)
                            if rect[0] != -32000 or rect[1] != -32000:
                                win32gui.SetWindowPos(
                                    dh, 0, -32000, -32000, 0, 0,
                                    win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE
                                )
                    except Exception:
                        pass

                # 2. Enumeração completa de todas as janelas do processo para ocultar qualquer outra
                hwnds = []
                win32gui.EnumWindows(lambda h, _: hwnds.append(h) or True, None)

                main_hwnd = None
                all_to_hide = []

                for h in hwnds:
                    _, win_pid_h = win32process.GetWindowThreadProcessId(h)
                    if win_pid_h == pid:
                        cls = win32gui.GetClassName(h)
                        title_h = win32gui.GetWindowText(h)

                        # Ignorar classes auxiliares do Windows
                        if cls in ("IME", "MSCTFIME UI", "ComboLBox"):
                            continue

                        # Qualquer janela com título ou visível é candidata a ocultar
                        if win32gui.IsWindowVisible(h) or title_h:
                            all_to_hide.append(h)

                        # Identificar a janela operacional principal (diálogo Capture Audio)
                        if cls == "#32770" or title_h == "Capture Audio":
                            main_hwnd = h
                        elif not main_hwnd and title_h and "whisper" in title_h.lower():
                            main_hwnd = h

                # Atualizar a referência da janela operacional principal
                self._whisper_hwnd = main_hwnd

                # 3. Ocultar e mover para fora da tela todas as janelas identificadas
                for h in all_to_hide:
                    try:
                        if win32gui.IsWindowVisible(h):
                            win32gui.ShowWindow(h, win32con.SW_HIDE)
                            log_debug(f"Janela oculta: HWND={h}, Classe={win32gui.GetClassName(h)}, Título={win32gui.GetWindowText(h)}")
                        rect = win32gui.GetWindowRect(h)
                        if rect[0] != -32000 or rect[1] != -32000:
                            win32gui.SetWindowPos(
                                h, 0, -32000, -32000, 0, 0,
                                win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE
                            )
                    except Exception:
                        pass

                # 4. Sincroniza continuamente o estado do Capture (gravação)
                if self._whisper_hwnd:
                    self._sync_capture_state()

            except Exception as err:
                log_debug(f"Erro no loop do gerenciador da GUI: {err}")

            # Intervalo adaptativo:
            #   0–15s: 1ms (janela pode aparecer durante carregamento do modelo, que demora)
            #   15–60s ou após mudança de estado: 50ms (vigilância moderada)
            #   >60s: 100ms (estabilidade)
            state_changed_recently = (time.time() - getattr(self, '_last_state_change_time', 0.0)) < 5.0
            elapsed = time.time() - start_time
            if elapsed < 15.0:
                sleep_time = 0.001
            elif elapsed < 60.0 or state_changed_recently:
                sleep_time = 0.05
            else:
                sleep_time = 0.1
            time.sleep(sleep_time)
        
        log_debug(f"Gerenciador da GUI do WhisperDesktop finalizado para o PID {pid}.")
        self._whisper_hwnd = None

    def set_capture_state(self, active: bool) -> bool:
        """Define o estado de gravação desejado e dispara a sincronização."""
        log_debug(f"set_capture_state acionado para active={active}.")
        self._desired_capture_state = active
        self._last_state_change_time = time.time()
        self._sync_capture_state()
        return True

    def _sync_capture_state(self):
        """Sincroniza dinamicamente o estado do Capture do WhisperDesktop com o estado desejado."""
        if not self._whisper_hwnd or self._desired_capture_state is None:
            return
            
        try:
            import win32gui
            import win32con
        except ImportError:
            return
            
        children = []
        try:
            win32gui.EnumChildWindows(self._whisper_hwnd, lambda h, _: children.append(h) or True, None)
        except Exception as e:
            log_debug(f"Erro ao enumerar controles do WhisperDesktop na sincronização: {e}")
            return
            
        # Analisa os botões disponíveis
        has_capture_button = False
        has_stop_button = False
        capture_btn_hwnd = None
        stop_btn_hwnd = None
        
        for child_hwnd in children:
            try:
                class_name = win32gui.GetClassName(child_hwnd)
                title = win32gui.GetWindowText(child_hwnd)
                if class_name == "Button":
                    norm_title = title.replace("&", "").strip().lower()
                    if norm_title in ["capture", "capturar", "gravar"]:
                        has_capture_button = True
                        capture_btn_hwnd = child_hwnd
                    elif norm_title in ["stop", "parar"]:
                        has_stop_button = True
                        stop_btn_hwnd = child_hwnd
            except Exception:
                pass
                
        # Sincroniza baseado no estado desejado:
        if self._desired_capture_state: # Queremos Capturando
            # Se ainda tem o botão de "Capture" (gravar), significa que está parado. Clicamos!
            if has_capture_button and capture_btn_hwnd:
                win32gui.SendMessage(capture_btn_hwnd, win32con.BM_CLICK, 0, 0)
                log_debug("Sincronizador: Botão 'Capture' pressionado para iniciar captura de áudio.")
        else: # Queremos Parado
            # Se tem o botão de "Stop" (parar), significa que está gravando. Clicamos!
            if has_stop_button and stop_btn_hwnd:
                win32gui.SendMessage(stop_btn_hwnd, win32con.BM_CLICK, 0, 0)
                log_debug("Sincronizador: Botão 'Stop' pressionado para pausar captura de áudio.")

    def stop(self):
        log_debug("Parando motor de transcrição...")
        self._running = False
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=1.0)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None

        # Garante a aniquilação completa de todas as instâncias do WhisperDesktop restantes
        try:
            import psutil
            for p in psutil.process_iter(['name']):
                if p.info['name'] and p.info['name'].lower() in ('whisperdesktop.exe', 'whisper-stream.exe'):
                    try:
                        p.kill()
                        log_debug(f"[stop] Processo zumbi morto no final: {p.info['name']} (PID: {p.pid})")
                    except Exception:
                        pass
        except Exception:
            pass
            
        try:
            subprocess.run(["taskkill", "/F", "/IM", "WhisperDesktop.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            pass

        log_debug("Motor parado com sucesso.")
