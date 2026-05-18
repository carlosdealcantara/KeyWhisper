import os
import sys
import time
import winsound
import threading
from audio_recorder import AudioRecorder
from ai_engine import AIEngine
from text_injector import get_active_window, inject_text
from hotkey_manager import HotkeyManager
from model_manager import ModelManager
from ui_overlay import StatusPopup
from ui_windows import OnboardingWindow, SettingsWindow
from tray_icon import TrayIcon

class KeyWhisperApp:
    def __init__(self):
        self.state = "IDLE" # Estados: IDLE, RECORDING, PROCESSING
        
        # Inicializa os módulos
        self.recorder = AudioRecorder()
        self.model_manager = ModelManager()
        self.popup = StatusPopup()
        self.tray = TrayIcon()
        self.hotkey = HotkeyManager(hotkey="f9")
        
        # Estado do modelo
        self.current_model = "medium"
        self.ai = None # Só inicializa depois de escolher o modelo
        
        self.target_hwnd = None # Guarda a janela que estava ativa
        self.model_loaded = False # Trava para não deixar gravar sem carregar

    def beep_start(self):
        winsound.Beep(1000, 200)

    def beep_stop(self):
        winsound.Beep(800, 200)
        winsound.Beep(600, 150)

    def on_hotkey(self):
        if self.state == "IDLE":
            self.start_workflow()
        elif self.state == "RECORDING":
            self.stop_workflow()

    def start_workflow(self):
        if not self.model_loaded:
            print("AVISO: Modelo ainda não está pronto ou falhou ao carregar. Aguarde.")
            winsound.Beep(500, 500) # Som de erro
            return

        self.target_hwnd = get_active_window()
        self.state = "RECORDING"
        self.beep_start()
        self.popup.set_status("Ouvindo...")
        self.popup.show()
        self.recorder.start_recording()

    def stop_workflow(self):
        self.state = "PROCESSING"
        self.beep_stop()
        self.popup.set_status("Processando...")
        audio_file = self.recorder.stop_recording()
        
        if not audio_file:
            print("ERRO: Nenhum arquivo de áudio foi gerado.")
            self.popup.hide()
            self.state = "IDLE"
            return

        print(f"Áudio gravado. Iniciando processamento de {audio_file}...")
        threading.Thread(target=self._process_audio, args=(audio_file,), daemon=True).start()

    def _process_audio(self, audio_file):
        try:
            if self.ai:
                text = self.ai.transcribe(audio_file)
                print(f"Resultado da transcrição: '{text}'")
                
                # Esconde o popup NA THREAD PRINCIPAL
                def hide_popup():
                    self.popup.hide()
                self.popup.root.after(0, hide_popup)
                
                if text:
                    print(f"Injetando texto na janela {self.target_hwnd}...")
                    inject_text(text, self.target_hwnd)
                else:
                    print("Texto vazio. Nada a injetar.")
            else:
                print("ERRO: IA não inicializada!")
                def hide_popup():
                    self.popup.hide()
                self.popup.root.after(0, hide_popup)
                
        except Exception as e:
            print(f"Erro crítico no processamento: {e}")
            def hide_popup():
                self.popup.hide()
            self.popup.root.after(0, hide_popup)
        finally:
            self.recorder.cleanup()
            self.state = "IDLE"
            print("Fluxo finalizado. Pronto para nova gravação.")

    def on_settings(self):
        print("Abrindo configurações...")
        settings_win = SettingsWindow(
            self.popup.root, 
            self.model_manager, 
            self.current_model,
            self.on_model_changed
        )
        settings_win.show()

    def on_help(self):
        print("Ajuda clicada.")

    def on_model_changed(self, new_model):
        print(f"Trocando modelo para: {new_model}")
        self.current_model = new_model
        self.model_loaded = False
        # Recarrega o modelo na IA
        self.ai = AIEngine(model_size=new_model, download_root=self.model_manager.download_root)
        
        def reload_thread():
            success = self.ai.load_model()
            if success:
                self.model_loaded = True
                print("Novo modelo carregado e pronto.")
            else:
                print("ERRO: Falha ao carregar o novo modelo.")
                self.model_loaded = False
                # Tenta fallback para outros modelos instalados
                self._try_fallback()
            
        threading.Thread(target=reload_thread, daemon=True).start()

    def _try_fallback(self):
        """Tenta carregar qualquer outro modelo instalado se o atual falhar."""
        installed = self.model_manager.get_installed_models()
        # Ordem de preferência para fallback
        preference = ["medium", "small", "tiny"]
        
        for model in preference:
            if model in installed and model != self.current_model:
                print(f"Tentando fallback automático para o modelo instalado: {model}")
                self.current_model = model
                self._initialize_ai()
                return
                
        print("CRÍTICO: Nenhum modelo alternativo encontrado ou instalado.")

    def on_exit(self):
        self.hotkey.cleanup()
        self.recorder.cleanup()
        self.popup.quit()
        sys.exit(0)

    def on_onboarding_complete(self, selected_model):
        print(f"Onboarding completo. Modelo selecionado: {selected_model}")
        self.current_model = selected_model
        self._initialize_ai()

    def _initialize_ai(self):
        """Inicializa a IA com o modelo atual."""
        self.ai = AIEngine(model_size=self.current_model, download_root=self.model_manager.download_root)
        
        def load_thread():
            success = self.ai.load_model()
            if success:
                self.model_loaded = True
                print("App pronto para uso.")
            else:
                print("ERRO: Não foi possível carregar o modelo atual.")
                self.model_loaded = False
                self._try_fallback()
            
        threading.Thread(target=load_thread, daemon=True).start()

    def run(self):
        self.popup.create_window()
        self.popup.hide()
        
        installed_models = self.model_manager.get_installed_models()
        
        if not installed_models:
            print("Nenhum modelo encontrado. Iniciando onboarding...")
            onboarding = OnboardingWindow(
                self.popup.root, 
                self.model_manager, 
                self.on_onboarding_complete
            )
            onboarding.show()
        else:
            # Se já tem modelos, usa o primeiro da lista como padrão
            self.current_model = installed_models[0]
            print(f"Modelos encontrados. Usando padrão: {self.current_model}")
            self._initialize_ai()

        self.tray.setup(self.on_settings, self.on_exit)
        self.hotkey.setup(self.on_hotkey)
        self.popup.set_callbacks(self.on_settings, self.on_help)
        
        print("Loop principal iniciado.")
        self.popup.start_loop()

if __name__ == "__main__":
    app = KeyWhisperApp()
    app.run()
