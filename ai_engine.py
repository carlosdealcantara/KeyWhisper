import os
from faster_whisper import WhisperModel

class AIEngine:
    def __init__(self, model_size="medium", download_root=None):
        self.model_size = model_size
        self.download_root = download_root or os.path.join(os.environ.get('LOCALAPPDATA', ''), 'KeyWhisper', 'models')
        self.model = None
        self.device = "cuda" # Voltando para CUDA por padrão
        self.compute_type = "float16"
        
        # Jargões técnicos para viciar o modelo
        self.initial_prompt = (
            "slug, branch, dev, main, deploy, commit, merge, breadcrumbs, javascript, python, "
            "html, css, react, node, api, rest, json, database, sql, docker, git, github, gitlab, "
            "frontend, backend, fullstack, agile, scrum, kanban, sprint, bug, debug, refactor"
        )

    def load_model(self):
        """Carrega o modelo na memória/VRAM. Tenta CUDA e faz fallback para CPU."""
        print(f"Tentando carregar modelo '{self.model_size}' no dispositivo 'cuda'...")
        
        try:
            self.model = WhisperModel(
                self.model_size,
                device="cuda",
                compute_type="float16",
                download_root=self.download_root
            )
            self.device = "cuda"
            self.compute_type = "float16"
            print("Modelo carregado com sucesso na GPU (CUDA)!")
            return True
        except Exception as e:
            print(f"Erro ao carregar no CUDA: {e}")
            print("Tentando fallback para CPU...")
            try:
                self.model = WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type="int8",
                    download_root=self.download_root
                )
                self.device = "cpu"
                self.compute_type = "int8"
                print("Modelo carregado com sucesso na CPU!")
                return True
            except Exception as e2:
                print(f"Erro no fallback para CPU: {e2}")
                return False

    def transcribe(self, audio_path):
        """Transcreve o arquivo de áudio."""
        if not self.model:
            print("ERRO: Modelo não está carregado!")
            return ""

        if not os.path.exists(audio_path):
            print(f"ERRO: Arquivo de áudio não encontrado: {audio_path}")
            return ""

        file_size = os.path.getsize(audio_path)
        print(f"Iniciando transcrição. Arquivo: {audio_path} ({file_size} bytes)")
        
        if file_size < 1000:
            print("AVISO: Arquivo de áudio muito pequeno. Pode estar vazio.")

        try:
            # Mantendo vad_filter=False para evitar o erro do arquivo ONNX
            segments, info = self.model.transcribe(
                audio_path,
                language="pt",
                initial_prompt=self.initial_prompt,
                vad_filter=False
            )

            print(f"Idioma detectado: {info.language} com probabilidade {info.language_probability:.2f}")

            text_parts = []
            for segment in segments:
                print(f"Trecho detectado [{segment.start:.2f}s -> {segment.end:.2f}s]: {segment.text}")
                text_parts.append(segment.text)

            full_text = "".join(text_parts).strip()
            print(f"Transcrição completa concluída. Texto gerado: '{full_text}'")
            return full_text
        except Exception as e:
            print(f"ERRO durante a transcrição: {e}")
            return ""
