import ctypes
import ctypes.wintypes
import threading
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Constantes da API do Windows
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

# Mapeamento para teclas virtuais (Virtual Key Codes) comuns
VK_MAP = {
    # Teclas de Função
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74, "f6": 0x75,
    "f7": 0x76, "f8": 0x77, "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    # Números
    "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34, "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
}

class HotkeyManager:
    _id_counter = 100  # IDs exclusivos para registrar os hotkeys

    def __init__(self, hotkey="f9"):
        self.hotkey = hotkey.lower()
        self.callback = None
        self.thread = None
        self.thread_id = None
        self.running = False
        
        # Atribui um ID exclusivo de hotkey
        self.hotkey_id = HotkeyManager._id_counter
        HotkeyManager._id_counter += 1

    def setup(self, callback):
        """Define o callback que será chamado quando o atalho for pressionado."""
        self.callback = callback
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def update_hotkey(self, new_hotkey, callback):
        """Remove o atalho antigo e configura um novo dinamicamente."""
        print(f"[Hotkey] Atualizando atalho nativo de '{self.hotkey.upper()}' para '{new_hotkey.upper()}'...")
        self.cleanup()
        self.hotkey = new_hotkey.lower()
        self.setup(callback)

    def _loop(self):
        """Loop de mensagens do thread que registra o atalho do Windows."""
        # Salva o Thread ID atual para poder receber mensagens de encerramento
        self.thread_id = kernel32.GetCurrentThreadId()

        # Decodifica modificadores e tecla
        modifiers = MOD_NOREPEAT
        vk = 0
        
        parts = self.hotkey.split("+")
        for part in parts:
            part = part.strip()
            if part in ("ctrl", "control"):
                modifiers |= MOD_CONTROL
            elif part == "shift":
                modifiers |= MOD_SHIFT
            elif part == "alt":
                modifiers |= MOD_ALT
            elif part == "win":
                modifiers |= MOD_WIN
            else:
                # Procura no mapa
                vk = VK_MAP.get(part, 0)
                if not vk and len(part) == 1:
                    vk = ord(part.upper())

        if not vk:
            print(f"[Hotkey] Erro: Atalho inválido ou tecla não mapeada: {self.hotkey}")
            self.running = False
            return

        # Registra o hotkey global na fila de mensagens do thread atual
        res = user32.RegisterHotKey(None, self.hotkey_id, modifiers, vk)
        if not res:
            print(f"[Hotkey] Falha crítica ao registrar atalho nativo '{self.hotkey.upper()}' (código do erro: {kernel32.GetLastError()}).")
            self.running = False
            return

        print(f"[Hotkey] Atalho nativo '{self.hotkey.upper()}' registrado com sucesso (ID: {self.hotkey_id}).")

        msg = ctypes.wintypes.MSG()
        while self.running:
            # GetMessage bloqueia o thread até que uma mensagem seja postada na fila
            res = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if res <= 0:  # WM_QUIT ou erro
                break
                
            if msg.message == WM_HOTKEY:
                if msg.wParam == self.hotkey_id:
                    if self.callback:
                        try:
                            self.callback()
                        except Exception as e:
                            print(f"[Hotkey] Erro ao disparar callback: {e}")
                            
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        # Desregistra o atalho ao sair
        user32.UnregisterHotKey(None, self.hotkey_id)
        print(f"[Hotkey] Atalho nativo (ID: {self.hotkey_id}) desregistrado.")

    def cleanup(self):
        """Para o thread e libera o hotkey registrado."""
        self.running = False
        if self.thread_id:
            # Envia a mensagem WM_QUIT (0x0012) para que o GetMessage saia do bloqueio
            user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=1.0)
        self.thread_id = None
        self.thread = None
