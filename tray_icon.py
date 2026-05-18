import threading
from PIL import Image, ImageDraw
import pystray

class TrayIcon:
    def __init__(self):
        self.icon = None
        self.settings_callback = None
        self.exit_callback = None
        self.thread = None

    def _create_image(self):
        """Gera uma imagem simples para o ícone da bandeja."""
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), color='#1e1e2e')
        dc = ImageDraw.Draw(image)
        
        # Desenha um círculo roxo/azul elegante
        dc.ellipse((10, 10, 54, 54), fill='#89b4fa', outline='#b4befe')
        
        # Desenha a letra 'W' (de Whisper) no centro
        dc.text((24, 20), "W", fill="#11111b")
        
        return image

    def _run_icon(self):
        menu = pystray.Menu(
            pystray.MenuItem("Configurações", self._on_settings),
            pystray.MenuItem("Sair", self._on_exit)
        )
        
        self.icon = pystray.Icon(
            "KeyWhisper",
            self._create_image(),
            "KeyWhisper",
            menu
        )
        
        self.icon.run()

    def setup(self, settings_cb, exit_cb):
        self.settings_callback = settings_cb
        self.exit_callback = exit_cb
        
        # O pystray precisa rodar em sua própria thread para não travar a UI
        self.thread = threading.Thread(target=self._run_icon, daemon=True)
        self.thread.start()
        print("Ícone da bandeja iniciado.")

    def _on_settings(self):
        if self.settings_callback:
            self.settings_callback()

    def _on_exit(self):
        if self.exit_callback:
            self.exit_callback()
        if self.icon:
            self.icon.stop()

    def stop(self):
        if self.icon:
            self.icon.stop()
        if self.thread:
            self.thread.join(timeout=1)
