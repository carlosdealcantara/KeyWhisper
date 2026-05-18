import keyboard

class HotkeyManager:
    def __init__(self, hotkey="f9"):
        self.hotkey = hotkey
        self.callback = None

    def setup(self, callback):
        """Define o callback que será chamado quando o atalho for pressionado."""
        self.callback = callback
        # Adiciona o listener global
        keyboard.add_hotkey(self.hotkey, self._on_hotkey_pressed)
        print(f"Atalho {self.hotkey.upper()} configurado.")

    def _on_hotkey_pressed(self):
        if self.callback:
            # Chama o callback. Como o keyboard roda em sua própria thread,
            # o callback também rodará nela.
            self.callback()

    def cleanup(self):
        """Remove todos os atalhos configurados."""
        keyboard.unhook_all()
        print("Atalhos desconfigurados.")
