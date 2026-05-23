import os
import time
import win32gui
import win32con


def log_debug(message):
    log_dir = os.path.join(os.environ.get('APPDATA', ''), 'KeyWhisper')
    try:
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "debug_log.txt"), "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except Exception:
        pass

def set_active_window(hwnd):
    """Define a janela ativa de volta para o handle fornecido de forma ultra robusta."""
    if not hwnd:
        return False
    try:
        import win32process
        import win32api
        
        # Se a janela estiver minimizada, restaura
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.05)

        fore_hwnd = win32gui.GetForegroundWindow()
        if fore_hwnd == hwnd:
            return True

        # Pressiona e solta a tecla ALT (VK_MENU = 0x12) para burlar a restrição de foco do Windows (SetForegroundWindow)
        # Ao simular um evento de teclado, o Windows nos dá a permissão temporária de alterar a janela ativa.
        win32api.keybd_event(0x12, 0, 0, 0)
        win32api.keybd_event(0x12, 0, win32con.KEYEVENTF_KEYUP, 0)
        
        # AttachThreadInput conecta as filas de entrada do thread atual e do thread da janela ativa
        if fore_hwnd:
            fore_thread_id, _ = win32process.GetWindowThreadProcessId(fore_hwnd)
            curr_thread_id = win32api.GetCurrentThreadId()
            target_thread_id, _ = win32process.GetWindowThreadProcessId(hwnd)
            
            # Anexa o thread atual ao thread de foreground
            attached_fore = False
            attached_target = False
            
            try:
                if fore_thread_id != curr_thread_id:
                    win32process.AttachThreadInput(curr_thread_id, fore_thread_id, True)
                    attached_fore = True
            except Exception as e:
                log_debug(f"[Injector] Aviso AttachThreadInput foreground: {e}")
                
            try:
                if target_thread_id != curr_thread_id:
                    win32process.AttachThreadInput(curr_thread_id, target_thread_id, True)
                    attached_target = True
            except Exception as e:
                log_debug(f"[Injector] Aviso AttachThreadInput target: {e}")

            # Define o foco do teclado para a janela alvo
            win32gui.SetForegroundWindow(hwnd)
            win32gui.BringWindowToTop(hwnd)
            win32gui.SetFocus(hwnd)
            
            # Desconecta os inputs
            if attached_fore:
                try:
                    win32process.AttachThreadInput(curr_thread_id, fore_thread_id, False)
                except Exception:
                    pass
            if attached_target:
                try:
                    win32process.AttachThreadInput(curr_thread_id, target_thread_id, False)
                except Exception:
                    pass
        else:
            win32gui.SetForegroundWindow(hwnd)
            win32gui.BringWindowToTop(hwnd)
            win32gui.SetFocus(hwnd)
            
        log_debug(f"[Injector] Sucesso ao setar janela foreground HWND={hwnd}")
        return True
    except Exception as e:
        log_debug(f"[Injector] Erro ao focar na janela HWND={hwnd}: {e}")
        # Fallback simples
        try:
            win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception:
            return False

def inject_text(text, target_hwnd=None):
    """
    Injeta o texto na janela ativa ou na janela especificada por target_hwnd
    usando digitação nativa Unicode com a API SendInput do Windows.
    Não altera ou interfere em nada no Clipboard do usuário (preserva prints, arquivos, etc.).
    """
    if not text:
        log_debug("[Injector] Cancelado: nenhum texto fornecido.")
        return

    log_debug(f"[Injector] Iniciando digitação nativa de '{text}'...")

    # Determina a melhor janela para digitar
    current_active = win32gui.GetForegroundWindow()
    is_system_desktop = False
    if current_active:
        try:
            class_name = win32gui.GetClassName(current_active)
            title = win32gui.GetWindowText(current_active)
            if class_name in ["Shell_TrayWnd", "Shell_SecondaryTrayWnd", "WorkerW", "Progman", "DV2ControlHost"]:
                is_system_desktop = True
            if "KeyWhisper" in title and "Visual Studio Code" not in title and "Google Chrome" not in title and "Firefox" not in title and "Edge" not in title:
                is_system_desktop = True
        except Exception:
            pass

    if current_active and not is_system_desktop:
        log_debug(f"[Injector] Usando janela ativa atual (HWND={current_active}) para digitação de forma dinâmica.")
    elif target_hwnd:
        if current_active != target_hwnd:
            log_debug(f"[Injector] Janela ativa atual ({current_active}) é inválida ou Área de Trabalho. Restaurando foco para o alvo original ({target_hwnd})...")
            set_active_window(target_hwnd)
            time.sleep(0.15)
        else:
            log_debug(f"[Injector] Janela alvo ({target_hwnd}) já está em foco. Evitando desativar cursor.")

    # Digitação nativa de caracteres Unicode usando SendInput corrigido de 40 bytes
    try:
        import ctypes
        from ctypes import wintypes
        
        KEYEVENTF_UNICODE = 0x0004
        KEYEVENTF_KEYUP = 0x0002
        INPUT_KEYBOARD = 1

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [
                ("dx", wintypes.LONG),
                ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_void_p)
            ]

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_void_p)
            ]

        class HARDWAREINPUT(ctypes.Structure):
            _fields_ = [
                ("uMsg", wintypes.DWORD),
                ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD)
            ]

        class INPUT_UNION(ctypes.Union):
            _fields_ = [
                ("mi", MOUSEINPUT),
                ("ki", KEYBDINPUT),
                ("hi", HARDWAREINPUT)
            ]

        class INPUT(ctypes.Structure):
            _fields_ = [
                ("type", wintypes.DWORD),
                ("union", INPUT_UNION)
            ]

        SendInput = ctypes.windll.user32.SendInput
        SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
        SendInput.restype = wintypes.UINT

        # Normaliza múltiplos espaços dentro do texto para evitar os "espaços gigantes",
        # mas garante que termine com um espaço simples para separar falas consecutivas
        text = " ".join(text.split()) + " "

        inputs = (INPUT * 2)()

        for char in text:
            char_code = ord(char)
            # Evento Key Down
            inputs[0].type = INPUT_KEYBOARD
            inputs[0].union.ki = KEYBDINPUT(0, char_code, KEYEVENTF_UNICODE, 0, None)
            # Evento Key Up
            inputs[1].type = INPUT_KEYBOARD
            inputs[1].union.ki = KEYBDINPUT(0, char_code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, None)
            
            SendInput(2, inputs, ctypes.sizeof(INPUT))
            
            # Pausa cirúrgica de 1 milissegundo para dar tempo a motores síncronos (como o Bloco de Notas)
            # digerirem a tecla e evitarem o descarte de letras pelo spellcheck.
            time.sleep(0.001)
        
        log_debug(f"[Injector] Digitação nativa fluida concluída com sucesso ({len(text)} caracteres).")
    except Exception as e:
        log_msg = f"[Injector] Erro ao injetar via SendInput nativo corrigido: {e}"
        print(log_msg)
        log_debug(log_msg)
