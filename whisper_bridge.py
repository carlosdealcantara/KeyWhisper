import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def log_debug(message):
    log_dir = os.path.join(os.environ.get('APPDATA', ''), 'KeyWhisper')
    try:
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "debug_log.txt"), "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except Exception:
        pass

class FileUpdateHandler(FileSystemEventHandler):
    def __init__(self, file_path, callback):
        super().__init__()
        self.file_path = os.path.abspath(file_path)
        self.callback = callback
        self.last_position = 0
        
        # Inicializa a posição se o arquivo já existir
        if os.path.exists(self.file_path):
            try:
                self.last_position = os.path.getsize(self.file_path)
            except Exception:
                self.last_position = 0
        log_msg = f"[WhisperBridge] Inicializado monitorando: '{self.file_path}' (Posição inicial: {self.last_position} bytes)"
        print(log_msg)
        log_debug(log_msg)

    def process_new_data(self):
        if not os.path.exists(self.file_path):
            log_debug(f"[WhisperBridge] process_new_data cancelado: arquivo não existe em '{self.file_path}'")
            return

        try:
            current_size = os.path.getsize(self.file_path)
            
            # Se o arquivo diminuiu ou foi recriado/limpo
            if current_size < self.last_position:
                log_debug(f"[WhisperBridge] Arquivo truncado ou recriado de {self.last_position} para {current_size} bytes. Resetando ponteiro.")
                self.last_position = 0

            if current_size > self.last_position:
                log_debug(f"[WhisperBridge] Tamanho aumentou de {self.last_position} para {current_size} bytes. Lendo novos dados...")
                with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                    f.seek(self.last_position)
                    new_text = f.read().replace('\ufeff', '')
                    self.last_position = f.tell()
                    
                    # Limpa espaços em branco vazios
                    clean_text = new_text.strip()
                    if clean_text:
                        log_debug(f"[WhisperBridge] Novo texto lido com sucesso: '{clean_text}'")
                        self.callback(clean_text)
                    else:
                        log_debug("[WhisperBridge] Novos bytes lidos eram apenas espaços em branco vazios.")
            else:
                log_debug(f"[WhisperBridge] Nenhuma alteração no tamanho do arquivo ({current_size} bytes).")
        except Exception as e:
            log_msg = f"[WhisperBridge] Erro ao ler atualizações do arquivo: {e}"
            print(log_msg)
            log_debug(log_msg)

    def on_modified(self, event):
        # Watchdog pode mandar eventos da pasta, filtramos pelo caminho exato do arquivo
        if os.path.abspath(event.src_path) == self.file_path:
            log_debug(f"[WhisperBridge] Evento ON_MODIFIED recebido para o caminho correto: '{event.src_path}'")
            self.process_new_data()

    def on_created(self, event):
        if os.path.abspath(event.src_path) == self.file_path:
            log_msg = "[WhisperBridge] Evento ON_CREATED recebido (Arquivo criado)."
            print(log_msg)
            log_debug(log_msg)
            self.last_position = 0
            self.process_new_data()


class WhisperBridge:
    def __init__(self, file_path, on_text_received):
        self.file_path = file_path
        self.on_text_received = on_text_received
        self.observer = None
        self.handler = None
        self.active = False

    def start(self):
        if self.active:
            return
            
        if not self.file_path:
            print("[WhisperBridge] AVISO: Caminho do arquivo não configurado. Ponte em espera.")
            return

        # Garante que a pasta pai existe
        dir_path = os.path.dirname(os.path.abspath(self.file_path))
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path, exist_ok=True)
            except Exception as e:
                print(f"[WhisperBridge] Erro ao criar pasta para o arquivo de saída: {e}")
                return

        self.handler = FileUpdateHandler(self.file_path, self.on_text_received)
        self.observer = Observer()
        
        # Watchdog monitora a pasta pai para capturar criação/modificação do arquivo
        self.observer.schedule(self.handler, path=dir_path, recursive=False)
        self.observer.start()
        self.active = True
        print(f"[WhisperBridge] Observador de sistema de arquivos ativo na pasta: {dir_path}")

    def stop(self):
        if not self.active:
            return
        
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=1.0)
            
        self.active = False
        self.observer = None
        self.handler = None
        print("[WhisperBridge] Observador de sistema de arquivos parado.")

    def update_file_path(self, new_file_path):
        """Altera o arquivo monitorado dinamicamente."""
        was_active = self.active
        self.stop()
        self.file_path = new_file_path
        if was_active:
            self.start()
