import customtkinter as ctk

class StatusPopup:
    def __init__(self):
        self.root = None
        self.label = None
        self.status_text = "Ouvindo..."
        self.settings_callback = None
        self.help_callback = None

    def create_window(self):
        self.root = ctk.CTk()
        
        # Configurações da janela para ser um popup flutuante
        self.root.title("KeyWhisper Status")
        self.root.overrideredirect(True) # Remove as bordas do Windows
        self.root.attributes("-topmost", True) # Sempre no topo
        
        # Tema escuro elegante
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
        # Tamanho e posição (centralizado no topo da tela)
        window_width = 300
        window_height = 50
        screen_width = self.root.winfo_screenwidth()
        
        # Posiciona no topo centralizado
        x = (screen_width // 2) - (window_width // 2)
        y = 50 # 50 pixels do topo
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.configure(fg_color="#1e1e2e") # Cor de fundo escura (Catppuccin crust-ish)

        # Frame principal com borda arredondada (simulada)
        main_frame = ctk.CTkFrame(self.root, fg_color="#1e1e2e", corner_radius=10)
        main_frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Círculo pulsante / Indicador (vamos usar um label com emoji ou texto por enquanto)
        self.indicator = ctk.CTkLabel(
            main_frame, 
            text="🔴", 
            font=("Segoe UI", 16),
            text_color="#f38ba8"
        )
        self.indicator.pack(side="left", padx=(15, 5))

        # Texto de status
        self.label = ctk.CTkLabel(
            main_frame, 
            text=self.status_text, 
            font=("Segoe UI", 14, "bold"),
            text_color="#cdd6f4"
        )
        self.label.pack(side="left", padx=5)

        # Botão de Ajuda
        btn_help = ctk.CTkButton(
            main_frame,
            text="❓",
            width=25,
            height=25,
            fg_color="transparent",
            text_color="#a6adc8",
            hover_color="#313244",
            command=self._on_help
        )
        btn_help.pack(side="right", padx=(5, 15))

        # Botão de Configurações
        btn_settings = ctk.CTkButton(
            main_frame,
            text="⚙️",
            width=25,
            height=25,
            fg_color="transparent",
            text_color="#a6adc8",
            hover_color="#313244",
            command=self._on_settings
        )
        btn_settings.pack(side="right", padx=5)

        # Efeito de piscar o círculo vermelho
        self._blink()

    def _blink(self):
        """Faz o emoji de círculo piscar."""
        if self.root:
            current_text = self.indicator.cget("text")
            if self.status_text == "Ouvindo...":
                self.indicator.configure(text="🔴" if current_text == "  " else "  ")
            else:
                self.indicator.configure(text="⏳") # Ampulheta para processando
            self.root.after(500, self._blink)

    def set_status(self, text):
        self.status_text = text
        if self.label:
            self.label.configure(text=text)

    def set_callbacks(self, settings_cb, help_cb):
        self.settings_callback = settings_cb
        self.help_callback = help_cb

    def _on_settings(self):
        if self.settings_callback:
            self.settings_callback()

    def _on_help(self):
        if self.help_callback:
            self.help_callback()

    def show(self):
        if not self.root:
            self.create_window()
        self.root.deiconify()
        self.root.update()

    def hide(self):
        if self.root:
            self.root.withdraw()

    def start_loop(self):
        if self.root:
            self.root.mainloop()

    def quit(self):
        if self.root:
            self.root.quit()
            self.root.destroy()
            self.root = None
