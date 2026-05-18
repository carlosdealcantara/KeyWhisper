import threading
import tempfile
import os
import queue
import sounddevice as sd
import scipy.io.wavfile as wavfile

class AudioRecorder:
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        self.recording = False
        self.audio_queue = queue.Queue()
        self.temp_file = None
        self.thread = None

    def _callback(self, indata, frames, time, status):
        """Este callback é chamado para cada bloco de áudio pelo sounddevice."""
        if status:
            print(f"Status do SoundDevice: {status}")
        self.audio_queue.put(indata.copy())

    def _record_thread(self):
        self.audio_queue = queue.Queue()
        # Criando um arquivo temporário que não é deletado automaticamente
        # para que possamos ler ele depois no módulo de IA.
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            self.temp_file = tf.name

        print(f"Gravando áudio para: {self.temp_file}")
        
        # Iniciando a captura do áudio
        with sd.InputStream(samplerate=self.sample_rate, channels=1, callback=self._callback):
            while self.recording:
                sd.sleep(100) # Dorme um pouco para não consumir CPU
                
        # Coletando todos os dados da fila
        audio_data = []
        while not self.audio_queue.empty():
            audio_data.append(self.audio_queue.get())
            
        if audio_data:
            import numpy as np
            # Concatena todos os blocos de áudio
            full_audio = np.concatenate(audio_data, axis=0)
            # Salva no arquivo WAV
            wavfile.write(self.temp_file, self.sample_rate, full_audio)
            print(f"Áudio salvo com sucesso. Tamanho: {len(full_audio)} frames.")
        else:
            print("Nenhum dado de áudio coletado.")
            self.temp_file = None

    def start_recording(self):
        if self.recording:
            print("Já está gravando.")
            return
        
        self.recording = True
        self.thread = threading.Thread(target=self._record_thread)
        self.thread.start()

    def stop_recording(self):
        if not self.recording:
            print("Não está gravando.")
            return None
        
        self.recording = False
        if self.thread:
            self.thread.join()
            
        return self.temp_file

    def cleanup(self):
        """Remove o arquivo temporário se ele existir."""
        if self.temp_file and os.path.exists(self.temp_file):
            try:
                os.remove(self.temp_file)
                print(f"Arquivo temporário removido: {self.temp_file}")
            except Exception as e:
                print(f"Erro ao remover arquivo temporário: {e}")
            self.temp_file = None
