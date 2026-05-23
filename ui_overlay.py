import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageDraw, ImageFont

import math

def get_premium_icon(icon_type, target_size):
    try:
        src_size = 128
        img = Image.new("RGBA", (src_size, src_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cx, cy = src_size // 2, src_size // 2

        if icon_type == "settings":
            # Engrenagem premium vazada no centro (linhas mais grossas)
            draw.ellipse((40, 40, 88, 88), outline="white", width=12)
            for i in range(8):
                a = math.radians(i * 45)
                x1 = cx + math.cos(a) * 20
                y1 = cy + math.sin(a) * 20
                x2 = cx + math.cos(a) * 44
                y2 = cy + math.sin(a) * 44
                draw.line((x1, y1, x2, y2), fill="white", width=12)
            # Fura o centro para ficar elegante
            draw.ellipse((48, 48, 80, 80), fill="black")
            
        elif icon_type == "mic":
            # Microfone clássico (estilo Windows nativo)
            draw.rounded_rectangle((50, 28, 78, 80), radius=14, fill="white")
            draw.arc((34, 40, 94, 100), start=0, end=180, fill="white", width=8)
            draw.line((34, 50, 34, 70), fill="white", width=8)
            draw.line((94, 50, 94, 70), fill="white", width=8)
            draw.line((64, 100, 64, 116), fill="white", width=8)
            draw.line((46, 116, 82, 116), fill="white", width=8)
            
        elif icon_type == "help":
            # Interrogação circular (linha mais grossa e fonte bold)
            draw.ellipse((16, 16, 112, 112), outline="white", width=8)
            try:
                font = ImageFont.truetype("segoeuib.ttf", 72) # Segoe UI Bold
            except Exception:
                try:
                    font = ImageFont.truetype("arialbd.ttf", 72) # Arial Bold
                except Exception:
                    font = ImageFont.load_default()
            draw.text((64, 61), "?", fill="white", font=font, anchor="mm")

        # Retorna a imagem redimensionada via CTkImage, usando o anti-aliasing do CTkImage (LANCZOS)
        return ctk.CTkImage(light_image=img, dark_image=img, size=(target_size, target_size))
        
    except Exception as e:
        print(f"[UI] Erro ao criar ícone premium {icon_type}: {e}")
        empty_img = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
        return ctk.CTkImage(light_image=empty_img, dark_image=empty_img, size=(target_size, target_size))

class ToastNotification:
    def __init__(self, parent_root):
        self.parent_root = parent_root
        self.root = None
        self.label = None

    def show(self, text="💬 Texto Injetado", duration_ms=1200):
        # Se já existir um toast aberto, fecha para abrir o novo
        if self.root:
            try:
                self.root.destroy()
            except Exception:
                pass
            self.root = None

        try:
            self.root = tk.Toplevel(self.parent_root)
            
            # Setup da janela
            self.root.title("KeyWhisper Toast")
            self.root.overrideredirect(True)
            self.root.attributes("-topmost", True)
            self.root.attributes("-alpha", 0.95) # Efeito de transparência sutil
            
            # Evita que a janela roube o foco do teclado
            self.root.wm_attributes("-toolwindow", True)
            try:
                import ctypes
                self.root.update_idletasks()
                hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
                GWL_EXSTYLE = -20
                WS_EX_NOACTIVATE = 0x08000000
                WS_EX_TOPMOST = 0x00000008
                
                style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE | WS_EX_TOPMOST)
                
                SWP_FRAMECHANGED = 0x0020
                SWP_NOACTIVATE = 0x0010
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 
                                                  SWP_FRAMECHANGED | SWP_NOACTIVATE | 
                                                  SWP_NOMOVE | SWP_NOSIZE)
            except Exception as ex:
                print(f"[Toast] Erro ao aplicar estilo sem foco: {ex}")
            
            # Cores Premium
            ctk.set_appearance_mode("Dark")
            
            # Tamanho e posicionamento (Canto inferior direito do monitor principal)
            window_width = 240
            window_height = 42
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # Posiciona 40px acima da barra de tarefas e 40px da direita
            x = screen_width - window_width - 40
            y = screen_height - window_height - 80
            
            self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
            self.root.configure(bg="#1f2937") # Cinza escuro premium
            
            # Frame interno com borda arredondada
            inner_frame = ctk.CTkFrame(
                self.root, 
                fg_color="#1f2937", 
                border_color="#10b981", # Borda esmeralda elegante
                border_width=1.5,
                corner_radius=8
            )
            inner_frame.pack(fill="both", expand=True)
            
            # Label de Texto
            self.label = ctk.CTkLabel(
                inner_frame,
                text=text,
                font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
                text_color="#10b981" # Texto esmeralda
            )
            self.label.pack(expand=True)

            # Auto-destruição após a duração especificada
            self.root.after(duration_ms, self._close)
            
            # Mostra sem focar
            self.root.deiconify()
            self.root.update()
            
        except Exception as e:
            print(f"[Toast] Erro ao desenhar toast: {e}")

    def _close(self):
        if self.root:
            try:
                self.root.destroy()
            except Exception:
                pass
            self.root = None

class ListeningPopup:
    def __init__(self, parent_root, on_close_callback, on_settings_callback, on_toggle_pause_callback=None):
        self.parent_root = parent_root
        self.on_close_callback = on_close_callback
        self.on_settings_callback = on_settings_callback
        self.on_toggle_pause_callback = on_toggle_pause_callback
        self.root = None
        self.drag_data = {"x": 0, "y": 0}
        self.is_paused = False

    def show(self):
        if self.root:
            return

        try:
            self.root = tk.Toplevel(self.parent_root)
            self.root.title("KeyWhisper Voice Overlay")
            self.root.overrideredirect(True)
            self.root.attributes("-topmost", True)
            self.root.attributes("-alpha", 0.98)
            
            # Setup da janela sem foco
            self.root.wm_attributes("-toolwindow", True)
            try:
                import ctypes
                self.root.update_idletasks()
                hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
                GWL_EXSTYLE = -20
                WS_EX_NOACTIVATE = 0x08000000
                WS_EX_TOPMOST = 0x00000008
                style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE | WS_EX_TOPMOST)
                
                SWP_FRAMECHANGED = 0x0020
                SWP_NOACTIVATE = 0x0010
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 
                                                  SWP_FRAMECHANGED | SWP_NOACTIVATE | 
                                                  SWP_NOMOVE | SWP_NOSIZE)
            except Exception as ex:
                print(f"[Popup] Erro ao aplicar estilo sem foco: {ex}")

            # Posicionamento (Centralizado no topo da tela principal)
            window_width = 250
            window_height = 110
            screen_width = self.root.winfo_screenwidth()
            
            # Centraliza no eixo X, e coloca a 45px do topo (eixo Y)
            x = (screen_width - window_width) // 2
            y = 45
            
            self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
            # Fundo especial que será tratado como transparente pelo Windows para bordas arredondadas perfeitas
            self.root.configure(bg="#000001")
            self.root.wm_attributes("-transparentcolor", "#000001")

            # Frame principal arredondado com borda sutil azul
            main_frame = ctk.CTkFrame(
                self.root,
                fg_color="#18181b",
                border_color="#2563eb",
                border_width=1.5,
                corner_radius=12
            )
            main_frame.pack(fill="both", expand=True)

            # Bind para arrastar a janela clicando no frame principal
            main_frame.bind("<Button-1>", self._start_drag)
            main_frame.bind("<B1-Motion>", self._drag_motion)

            # Alça de arrastar (pequena linha horizontal no topo)
            drag_handle = ctk.CTkFrame(
                main_frame,
                width=35,
                height=3,
                fg_color="#52525b",
                corner_radius=1.5
            )
            drag_handle.place(relx=0.5, rely=0.08, anchor="n")
            drag_handle.bind("<Button-1>", self._start_drag)
            drag_handle.bind("<B1-Motion>", self._drag_motion)

            # Botão de Fechar (✕) discreto no canto superior direito
            close_btn = ctk.CTkLabel(
                main_frame,
                text="✕",
                font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
                text_color="#71717a",
                cursor="hand2"
            )
            close_btn.place(relx=0.93, rely=0.06, anchor="ne")
            close_btn.bind("<Button-1>", lambda e: self.on_close_callback())

            # Status Label "Ouvindo" - centralizado verticalmente no terço superior
            self.status_label = ctk.CTkLabel(
                main_frame,
                text="Ouvindo",
                font=ctk.CTkFont(family="Segoe UI Variable Display", size=15, weight="bold"),
                text_color="#10b981"
            )
            self.status_label.place(relx=0.5, rely=0.5, anchor="center", y=-22)
            self.status_label.bind("<Button-1>", self._start_drag)
            self.status_label.bind("<B1-Motion>", self._drag_motion)

            # Container inferior para os botões de ação horizontais
            btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            btn_frame.place(relx=0.5, rely=0.5, anchor="center", y=22)

            # Botão de Configurações (⚙) - transparente, tamanho compacto
            self.settings_btn = ctk.CTkButton(
                btn_frame,
                text="",
                image=get_premium_icon("settings", 22),
                width=36,
                height=36,
                corner_radius=18,
                fg_color="transparent",
                hover_color="#27272a",
                command=self.on_settings_callback
            )
            self.settings_btn.pack(side="left", padx=4)

            # Botão Central de Microfone - círculo azul (com função de pause)
            self.mic_btn = ctk.CTkButton(
                btn_frame,
                text="",
                image=get_premium_icon("mic", 30),
                width=50,
                height=50,
                corner_radius=25,
                fg_color="#2563eb",
                hover_color="#3b82f6",
                command=self.on_toggle_pause_callback if self.on_toggle_pause_callback else lambda: None
            )
            self.mic_btn.pack(side="left", padx=8)

            # Inicia o loop de animação de pulsação e reticências
            self._animate_pulse()

            # Botão de Ajuda (?) - transparente, tamanho compacto
            self.help_btn = ctk.CTkButton(
                btn_frame,
                text="",
                image=get_premium_icon("help", 22),
                width=36,
                height=36,
                corner_radius=18,
                fg_color="transparent",
                hover_color="#27272a",
                command=self._show_help
            )
            self.help_btn.pack(side="left", padx=4)

            self.root.deiconify()
            self.root.update()

        except Exception as e:
            print(f"[Popup] Erro ao instanciar pop-up de escuta: {e}")

    def _start_drag(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def _drag_motion(self, event):
        deltax = event.x - self.drag_data["x"]
        deltay = event.y - self.drag_data["y"]
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def close(self):
        if self.root:
            try:
                self.root.destroy()
            except Exception:
                pass
            self.root = None

    def _show_help(self):
        help_win = tk.Toplevel(self.root)
        help_win.title("Ajuda - KeyWhisper")
        help_win.geometry("260x130")
        help_win.configure(bg="#18181b")
        help_win.attributes("-topmost", True)
        help_win.resizable(False, False)
        
        px = self.root.winfo_x() + (self.root.winfo_width() - 260) // 2
        py = self.root.winfo_y() + (self.root.winfo_height() - 130) // 2
        help_win.geometry(f"+{px}+{py}")

        frame = ctk.CTkFrame(help_win, fg_color="#18181b", border_color="#52525b", border_width=1, corner_radius=8)
        frame.pack(fill="both", expand=True, padx=4, pady=4)

        title = ctk.CTkLabel(frame, text="💡 Atalhos do KeyWhisper", font=ctk.CTkFont(family="Inter", size=13, weight="bold"), text_color="#3b82f6")
        title.pack(pady=(8, 4))

        info = ctk.CTkLabel(
            frame,
            text="• F9: Ativa / Pausa a escuta\n• Ctrl + Shift + F9: Configurações\n• Fale e o texto aparecerá no cursor!",
            font=ctk.CTkFont(family="Inter", size=11),
            text_color="#e4e4e7",
            justify="left"
        )
        info.pack(pady=4)

        ok_btn = ctk.CTkButton(
            frame,
            text="Entendido",
            width=80,
            height=24,
            corner_radius=4,
            fg_color="#2563eb",
            hover_color="#3b82f6",
            text_color="#ffffff",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=help_win.destroy
        )
        ok_btn.pack(pady=(4, 8))

    def set_paused(self, paused: bool):
        """Atualiza a UI para refletir o estado pausado/ouvindo."""
        self.is_paused = paused
        if not self.root:
            return
            
        if self.is_paused:
            self.mic_btn.configure(fg_color="#4b5563", hover_color="#6b7280")
            self.status_label.configure(text="Pausado", text_color="#9ca3af")
        else:
            self.mic_btn.configure(fg_color="#2563eb", hover_color="#3b82f6")
            self.status_label.configure(text="Ouvindo", text_color="#10b981")

    def _animate_pulse(self):
        """Loop de animação que pulsa a cor do botão e move as reticências do status."""
        if not self.root:
            return
            
        if not hasattr(self, 'pulse_step'):
            self.pulse_step = 0
            
        if not self.is_paused:
            # Animação de cor do microfone
            colors = ["#2563eb", "#2969f2", "#2d6ff9", "#3275ff", "#2d6ff9", "#2969f2"]
            try:
                self.mic_btn.configure(fg_color=colors[self.pulse_step % len(colors)])
            except Exception:
                pass
            
            # Removed dot animation for static 'Ouvindo' label
            # Previously: dots = "." * ((self.pulse_step // 2) % 4)
            # self.status_label.configure(text=f"Ouvindo{dots}")
            # Now we keep label unchanged

        
        self.pulse_step += 1
        self.root.after(150, self._animate_pulse)


class WelcomeWindow:
    def __init__(self, parent_root, on_close_callback=None):
        self.parent_root = parent_root
        self.on_close_callback = on_close_callback
        self.window = None

    def _close(self):
        self.window.destroy()
        if self.on_close_callback:
            self.on_close_callback()

    def show(self):
        """Desenha e exibe a tela de boas-vindas do KeyWhisper."""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.window.focus()
            return

        import settings

        self.window = ctk.CTkToplevel(self.parent_root)
        self.window.title("Bem-vindo ao KeyWhisper")
        self.window.geometry("585x280")
        self.window.resizable(False, False)

        # Centraliza na tela
        self.window.update_idletasks()
        width = 585
        height = 280
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

        self.window.configure(fg_color="#18181b")
        # Garante que a janela fique no topo e ganhe foco real para não ser jogada pra trás
        # pelo roubo de foco do motor WhisperDesktop. Força o topo por 5 segundos.
        self.window.attributes("-topmost", True)
        self.window.lift()
        self.window.focus_force()

        def enforce_focus(count):
            if not self.window or not self.window.winfo_exists():
                return
            if count > 0:
                self.window.lift()
                self.window.focus_force()
                self.window.after(500, lambda: enforce_focus(count - 1))
            else:
                self.window.attributes("-topmost", False)

        # Roda o reforço de foco 10 vezes (a cada 500ms) = 5 segundos de dominância
        self.window.after(500, lambda: enforce_focus(10))

        # Título principal
        title_label = ctk.CTkLabel(
            self.window,
            text="👋 Bem-vindo ao KeyWhisper!",
            font=ctk.CTkFont(family="Inter", size=24, weight="bold"),
            text_color="#3b82f6"
        )
        title_label.pack(pady=(25, 10))

        # Texto explicativo informativo
        message_text = (
            "O KeyWhisper está ativo! Ao reiniciar, ele será ativado em modo oculto.\n\n"
            "• Pressione F9 para exibir ou esconder este pop-up de escuta.\n"
            "• Pressione Ctrl + Shift + F9 para abrir a tela de configurações.\n\n"
            "Selecione um campo de texto, comece a falar e a transcrição aparecerá!"
        )
        msg_label = ctk.CTkLabel(
            self.window,
            text=message_text,
            font=ctk.CTkFont(family="Inter", size=14),
            text_color="#e4e4e7",
            wraplength=500,
            justify="left"
        )
        msg_label.pack(padx=40, pady=(5, 20))

        # A tela só deve aparecer na primeira vez ou quando acionada manualmente.
        self.config = settings.load_config()
        if self.config.get("show_welcome_on_startup", True):
            self.config["show_welcome_on_startup"] = False
            settings.save_config(self.config)

        # Botão Entendi
        start_btn = ctk.CTkButton(
            self.window,
            text="Entendi",
            width=140,
            height=40,
            corner_radius=8,
            fg_color="#2563eb",
            hover_color="#3b82f6",
            font=ctk.CTkFont(family="Inter", size=15, weight="bold"),
            command=self._close
        )
        start_btn.pack(pady=(10, 35))
