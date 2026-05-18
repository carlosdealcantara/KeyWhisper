import os
import shutil

# Silencia as barras de progresso do Hugging Face para não quebrar sem console
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

from huggingface_hub import snapshot_download

class ModelManager:
    def __init__(self, download_root=None):
        self.download_root = download_root or os.path.join(os.environ.get('LOCALAPPDATA', ''), 'KeyWhisper', 'models')
        self.available_models = {
            "tiny": "Systran/faster-whisper-tiny",
            "base": "Systran/faster-whisper-base",
            "small": "Systran/faster-whisper-small",
            "medium": "Systran/faster-whisper-medium",
            "large-v2": "Systran/faster-whisper-large-v2",
            "large-v3": "Systran/faster-whisper-large-v3"
        }

    def check_model_exists(self, model_size="medium"):
        model_path = os.path.join(self.download_root, f"faster-whisper-{model_size}")
        if os.path.exists(model_path):
            for root, dirs, files in os.walk(model_path):
                if files:
                    return True
        return False

    def get_installed_models(self):
        installed = []
        for size in self.available_models.keys():
            if self.check_model_exists(size):
                installed.append(size)
        return installed

    def delete_model(self, model_size):
        model_path = os.path.join(self.download_root, f"faster-whisper-{model_size}")
        if os.path.exists(model_path):
            try:
                shutil.rmtree(model_path)
                print(f"Modelo {model_size} excluído com sucesso.")
                return True
            except Exception as e:
                print(f"Erro ao excluir modelo {model_size}: {e}")
                return False
        return False

    def download_model(self, model_size="medium"):
        repo_id = self.available_models.get(model_size)
        if not repo_id:
            print(f"Modelo {model_size} não disponível.")
            return False

        print(f"Iniciando download do modelo {model_size} ({repo_id})...")
        try:
            snapshot_download(
                repo_id=repo_id,
                local_dir=os.path.join(self.download_root, f"faster-whisper-{model_size}"),
                local_dir_use_symlinks=False
            )
            print("Download concluído com sucesso!")
            return True
        except Exception as e:
            print(f"Erro ao baixar o modelo: {e}")
            return False

    def get_model_path(self, model_size="medium"):
        return os.path.join(self.download_root, f"faster-whisper-{model_size}")
