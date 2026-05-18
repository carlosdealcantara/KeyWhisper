import time
import win32gui
import win32con
import win32clipboard
import keyboard

def get_active_window():
    """Retorna o handle da janela ativa."""
    return win32gui.GetForegroundWindow()

def set_active_window(hwnd):
    """Define a janela ativa de volta para o handle fornecido."""
    try:
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception as e:
        print(f"Erro ao definir janela ativa: {e}")
        return False

def inject_text(text, target_hwnd=None):
    """
    Injeta o texto na janela ativa ou na janela especificada por target_hwnd
    usando a estratégia de Clipboard Hijack.
    """
    if not text:
        return

    # Se um handle foi especificado, tenta focar nele primeiro
    if target_hwnd:
        set_active_window(target_hwnd)
        time.sleep(0.1) # Pequena pausa para garantir o foco

    # 1. Salvar o conteúdo atual do clipboard (se for texto)
    old_text = ""
    try:
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            old_text = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
    except Exception as e:
        print(f"Aviso ao ler clipboard original: {e}")
        try: win32clipboard.CloseClipboard() 
        except: pass

    # 2. Colocar o novo texto no clipboard
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
        win32clipboard.CloseClipboard()
    except Exception as e:
        print(f"Erro ao definir clipboard: {e}")
        try: win32clipboard.CloseClipboard() 
        except: pass
        return

    # 3. Simular Ctrl+V
    time.sleep(0.05) # Estabilidade
    keyboard.send('ctrl+v')
    time.sleep(0.1) # Espera a colagem acontecer antes de restaurar

    # 4. Restaurar o clipboard original
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, old_text)
        win32clipboard.CloseClipboard()
    except Exception as e:
        print(f"Erro ao restaurar clipboard: {e}")
        try: win32clipboard.CloseClipboard() 
        except: pass
