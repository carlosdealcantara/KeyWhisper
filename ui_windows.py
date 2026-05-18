import customtkinter as ctk
import threading
import os
import time

class OnboardingWindow:
    def __init__(self, master, model_manager, on_complete_callback):
        self.master = master
        self.model_manager = model_manager
        self.on_complete_callback = on_complete_callback
        self.window = None
        self.selected_model = "medium"
        self.status_label = None
        self.download_button = None
        self.radio_buttons = []
        self.is_downloading = False

    def show(self):
        self.window = ctk.CTkToplevel(self.master)
        self.window.title("KeyWhisper - Configuração Inicial")
        self.window.geometry("620x480")
        self.window.attributes("-topmost", True)
        self.window.grab_set() # Torna a janela modal
        
        # Centralizar
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"+{x}+{y}")

        ctk.CTkLabel(
            self.window, 
            text="Bem-vindo ao KeyWhisper!", 
            font=("Segoe UI", 22, "bold")
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            self.window, 
            text="Para começar, precisamos baixar o modelo de Inteligência Artificial.\nEscolha a opção que melhor se adapta ao seu PC:",
            font=("Segoe UI", 13)
        ).pack(pady=10)

        # Frame para opções de modelo
        options_frame = ctk.CTkFrame(self.window)
        options_frame.pack(pady=20, padx=20, fill="x")

        self.radio_var = ctk.StringVar(value="medium")

        # Opção Recomendada (Medium)
        r1 = ctk.CTkRadioButton(
            options_frame, 
            text="Médio (Recomendado) - Melhor precisão, requer GPU razoável ou CPU boa.",
            variable=self.radio_var,
            value="medium"
        )
        r1.pack(anchor="w", pady=10, padx=10)
        self.radio_buttons.append(r1)

        # Opção Leve (Small)
        r2 = ctk.CTkRadioButton(
            options_frame, 
            text="Pequeno (Leve) - Mais rápido, usa menos memória, precisão aceitável.",
            variable=self.radio_var,
            value="small"
        )
        r2.pack(anchor="w", pady=10, padx=10)
        self.radio_buttons.append(r2)

        # Opção Avançada (Large)
        r3 = ctk.CTkRadioButton(
            options_frame, 
            text="Grande (Pesado) - Máxima precisão, requer GPU forte (VRAM > 4GB).",
            variable=self.radio_var,
            value="large-v3"
        )
        r3.pack(anchor="w", pady=10, padx=10)
        self.radio_buttons.append(r3)

        # Barra de Progresso
        self.progress_bar = ctk.CTkProgressBar(self.window, width=400)
        self.progress_bar.pack(pady=(10, 5))
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(
            self.window, 
            text="Pronto para baixar.", 
            font=("Segoe UI", 12, "italic"),
            text_color="#a6adc8"
        )
        self.status_label.pack(pady=5)

        self.download_button = ctk.CTkButton(
            self.window, 
            text="Baixar e Começar", 
            command=self._start_download,
            fg_color="#a6e3a1",
            text_color="#11111b",
            hover_color="#94e2d5",
            font=("Segoe UI", 13, "bold")
        )
        self.download_button.pack(pady=15)

    def _start_download(self):
        selected = self.radio_var.get()
        self.is_downloading = True
        
        self.download_button.configure(state="disabled", text="Baixando...")
        for rb in self.radio_buttons:
            rb.configure(state="disabled")
            
        self.status_label.configure(
            text="Conectando ao servidor Hugging Face...",
            text_color="#f9e2af"
        )
        
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()
        
        # Thread de download com retentativas
        threading.Thread(target=self._download_thread, args=(selected,), daemon=True).start()
        
        # Thread de monitoramento com tempo decorrido
        threading.Thread(target=self._monitor_folder_size, args=(selected,), daemon=True).start()

    def _get_folder_size_mb(self, folder):
        total_size = 0
        if os.path.exists(folder):
            for dirpath, dirnames, filenames in os.walk(folder):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.exists(fp):
                        total_size += os.path.getsize(fp)
        return total_size / (1024 * 1024)

    def _monitor_folder_size(self, model_size):
        model_dir = os.path.join(self.model_manager.download_root, f"faster-whisper-{model_size}")
        start_time = time.time()
        
        while self.is_downloading:
            size_mb = self._get_folder_size_mb(model_dir)
            elapsed = int(time.time() - start_time)
            
            # Mesmo que o tamanho seja 0 (baixando no cache), mostra o tempo passando
            if size_mb > 0:
                text = f"Baixando modelo... Já baixou aprox. {size_mb:.1f} MB.\nTempo decorrido: {elapsed}s"
            else:
                text = f"Buscando servidor e preparando arquivos...\nTempo decorrido: {elapsed}s"
                
            def update_text(t=text):
                self.status_label.configure(text=t, text_color="#f9e2af")
                
            try:
                self.window.after(0, update_text)
            except:
                break
            time.sleep(1) # Atualiza a cada segundo

    def _download_thread(self, model_size):
        success = False
        # Tenta 3 vezes antes de desistir
        for attempt in range(3):
            def update_status(a=attempt+1):
                self.status_label.configure(
                    text=f"Tentativa {a} de 3: Conectando...", 
                    text_color="#f9e2af"
                )
            try:
                self.window.after(0, update_status)
            except:
                pass
                
            success = self.model_manager.download_model(model_size)
            if success:
                break
            time.sleep(2) # Espera 2 segundos antes de tentar novamente
            
        self.is_downloading = False
        
        def update_ui():
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")
            
            if success:
                self.progress_bar.set(1.0)
                self.status_label.configure(text="Download concluído com sucesso!", text_color="#a6e3a1")
                self.download_button.configure(text="Concluir", state="normal", command=self._on_finish)
            else:
                self.progress_bar.set(0)
                self.status_label.configure(text="Erro ao baixar o modelo após 3 tentativas.\nVerifique sua internet e tente novamente.", text_color="#f38ba8")
                self.download_button.configure(state="normal", text="Tentar Novamente")
                for rb in self.radio_buttons:
                    rb.configure(state="normal")

        try:
            self.window.after(0, update_ui)
        except:
            pass

    def _on_finish(self):
        if self.on_complete_callback:
            self.on_complete_callback(self.radio_var.get())
        self.window.destroy()


class SettingsWindow:
    def __init__(self, master, model_manager, current_model, on_model_changed_callback):
        self.master = master
        self.model_manager = model_manager
        self.current_model = current_model
        self.on_model_changed_callback = on_model_changed_callback
        self.window = None
        self.models_frame = None

    def show(self):
        self.window = ctk.CTkToplevel(self.master)
        self.window.title("KeyWhisper - Configurações")
        self.window.geometry("550x450")
        self.window.attributes("-topmost", True)
        
        # Centralizar
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"+{x}+{y}")

        ctk.CTkLabel(
            self.window, 
            text="Configurações do KeyWhisper", 
            font=("Segoe UI", 18, "bold")
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            self.window, 
            text="Modelos Baixados no PC", 
            font=("Segoe UI", 14, "bold"),
            text_color="#89b4fa"
        ).pack(anchor="w", padx=20, pady=(10, 5))

        self.models_frame = ctk.CTkFrame(self.window)
        self.models_frame.pack(pady=10, padx=20, fill="both", expand=True)

        self._refresh_models_list()

        ctk.CTkLabel(
            self.window, 
            text="Nota: Modelos maiores ocupam mais espaço em disco (~1.5GB a 3GB+).", 
            font=("Segoe UI", 11, "italic"),
            text_color="#a6adc8"
        ).pack(pady=10)

    def _refresh_models_list(self):
        for widget in self.models_frame.winfo_children():
            widget.destroy()

        installed_models = self.model_manager.get_installed_models()
        
        if not installed_models and not hasattr(self, "downloading_model"):
            ctk.CTkLabel(self.models_frame, text="Nenhum modelo encontrado.").pack(pady=20)
            return

        for model in ["small", "medium", "large-v3"]:
            is_installed = model in installed_models
            is_active = model == self.current_model
            is_downloading = hasattr(self, "downloading_model") and self.downloading_model == model

            row_frame = ctk.CTkFrame(self.models_frame, fg_color="#313244" if is_active else "transparent")
            row_frame.pack(fill="x", padx=5, pady=2, ipady=5)

            status_text = "Ativo" if is_active else ("Baixando..." if is_downloading else ("Baixado" if is_installed else "Não baixado"))
            color = "#a6e3a1" if is_active else ("#f9e2af" if is_downloading else ("#89b4fa" if is_installed else "#a6adc8"))

            ctk.CTkLabel(
                row_frame, 
                text=f"{model.upper()}", 
                font=("Segoe UI", 12, "bold")
            ).pack(side="left", padx=10)

            ctk.CTkLabel(
                row_frame, 
                text=status_text, 
                font=("Segoe UI", 11),
                text_color=color
            ).pack(side="left", padx=10)

            if is_downloading:
                continue
                
            if is_installed and not is_active:
                ctk.CTkButton(
                    row_frame,
                    text="Excluir",
                    width=60,
                    height=20,
                    fg_color="#f38ba8",
                    text_color="#11111b",
                    hover_color="#eba0ac",
                    command=lambda m=model: self._delete_model(m)
                ).pack(side="right", padx=10)
                
                ctk.CTkButton(
                    row_frame,
                    text="Ativar",
                    width=60,
                    height=20,
                    fg_color="#f9e2af",
                    text_color="#11111b",
                    hover_color="#eba0ac",
                    command=lambda m=model: self._activate_model(m)
                ).pack(side="right", padx=5)
                
            elif not is_installed:
                ctk.CTkButton(
                    row_frame,
                    text="Baixar",
                    width=60,
                    height=20,
                    fg_color="#94e2d5",
                    text_color="#11111b",
                    hover_color="#89b4fa",
                    command=lambda m=model: self._download_new_model(m)
                ).pack(side="right", padx=10)

    def _delete_model(self, model_size):
        if self.model_manager.delete_model(model_size):
            self._refresh_models_list()

    def _activate_model(self, model_size):
        self.current_model = model_size
        if self.on_model_changed_callback:
            self.on_model_changed_callback(model_size)
        self._refresh_models_list()

    def _download_new_model(self, model_size):
        self.downloading_model = model_size
        self._refresh_models_list()
        
        def dl_thread():
            self.model_manager.download_model(model_size)
            delattr(self, "downloading_model")
            try:
                self.window.after(0, self._refresh_models_list)
            except:
                pass
            
        threading.Thread(target=dl_thread, daemon=True).start()
