import threading
import sys
from PIL import Image, ImageDraw
import pystray

def log_debug(message):
    """Encaminha log para o text_injector de forma segura."""
    try:
        from text_injector import log_debug as core_log
        core_log(message)
    except Exception:
        pass

class TrayIcon:
    def __init__(self):
        self.icon = None
        self.settings_callback = None
        self.exit_callback = None
        self.thread = None

    def _create_image(self, active=True):
        """Gera uma imagem de ícone em formato RGBA transparente de alta definição."""
        try:
            width = 64
            height = 64
            # Fundo transparente RGBA
            image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            dc = ImageDraw.Draw(image)
            
            # Cores premium
            state_color = '#2563eb' if active else '#6b7280' # Azul se ativo, cinza se inativo
            border_color = '#3b82f6' if active else '#9ca3af'
            
            # Círculo externo
            dc.ellipse((6, 6, 58, 58), fill=state_color, outline=border_color, width=4)
            
            # Carrega fonte em negrito para a bandeja
            from PIL import ImageFont
            font = None
            for fn in ["segoeuib.ttf", "arialbd.ttf", "calibrib.ttf", "trebucbd.ttf", "tahomabd.ttf"]:
                try:
                    # Tamanho de fonte 28px no canvas 64x64px.
                    # Isso preenche muito bem o círculo interno com diâmetro ~48px.
                    font = ImageFont.truetype(fn, 28)
                    break
                except Exception:
                    continue
            
            if not font:
                font = ImageFont.load_default()
                
            # Desenha "KW" no centro da imagem (centro é 32, 32)
            # Deslocamos em y=31 para um balanceamento visual impecável da fonte bold
            dc.text((32, 31), "KW", fill='#ffffff', font=font, anchor='mm')
            
            return image
        except Exception as e:
            log_debug(f"[Tray] Erro ao desenhar imagem do ícone: {e}")
            # Retorna uma imagem preta de fallback para não quebrar a execução
            return Image.new('RGBA', (64, 64), (0, 0, 0, 255))

    def _update_menu(self):
        """Atualiza dinamicamente o menu, tooltip e ícone da bandeja."""
        try:
            menu = pystray.Menu(
                pystray.MenuItem("Configurações", self._on_settings),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Sair", self._on_exit)
            )
            if self.icon:
                self.icon.menu = menu
        except Exception as e:
            log_debug(f"[Tray] Erro ao atualizar menu da bandeja: {e}")

    def set_bridge_state(self, enabled):
        if self.icon:
            self._update_menu()

    def _run_icon(self):
        """Thread worker para instanciar e rodar o pystray.Icon."""
        try:
            log_debug("[Tray] Preparando instância do pystray.Icon...")
            menu = pystray.Menu(
                pystray.MenuItem("Configurações", self._on_settings),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Sair", self._on_exit)
            )
            
            self.icon = pystray.Icon(
                "KeyWhisper",
                self._create_image(True),
                "KeyWhisper",
                menu
            )
            
            log_debug("[Tray] Iniciando loop de mensagens do pystray...")
            self.icon.run()
            log_debug("[Tray] Loop do pystray finalizado normalmente.")
        except Exception as e:
            import traceback
            log_debug(f"[Tray] Falha crítica no loop do ícone da bandeja: {e}\n{traceback.format_exc()}")

    def setup(self, settings_cb, exit_cb):
        """Inicia o ícone da bandeja em uma thread em background."""
        self.settings_callback = settings_cb
        self.exit_callback = exit_cb
        
        try:
            self.thread = threading.Thread(target=self._run_icon, daemon=True)
            self.thread.start()
            log_debug("[Tray] Thread do ícone da bandeja disparada.")
        except Exception as e:
            log_debug(f"[Tray] Erro ao disparar thread do ícone da bandeja: {e}")

    def _on_settings(self):
        if self.settings_callback:
            try:
                self.settings_callback()
            except Exception as e:
                log_debug(f"[Tray] Erro no callback de configurações: {e}")

    def _on_exit(self):
        log_debug("[Tray] Opção Sair selecionada pelo menu do ícone.")
        if self.exit_callback:
            try:
                self.exit_callback()
            except Exception as e:
                log_debug(f"[Tray] Erro no callback de saída: {e}")
        self.stop()

    def stop(self):
        """Para o ícone de forma limpa e aguarda a finalização do thread."""
        log_debug("[Tray] Parando ícone da bandeja...")
        if self.icon:
            try:
                self.icon.stop()
            except Exception as e:
                log_debug(f"[Tray] Erro ao parar pystray.Icon: {e}")
            self.icon = None
        if self.thread:
            try:
                self.thread.join(timeout=1.0)
            except Exception as e:
                log_debug(f"[Tray] Erro ao esperar finalização da thread: {e}")
            self.thread = None
        log_debug("[Tray] Ícone da bandeja finalizado.")
