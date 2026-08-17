import subprocess
import time
import modal
from pathlib import Path

# 使用するカスタムノードのリスト
NODES = [ "https://github.com/MoonGoblinDev/Civicomfy.git",  ]

# Volumeの作成
model_volume = modal.Volume.from_name("comfy-models", create_if_missing=True)
output_volume = modal.Volume.from_name("comfy-output", create_if_missing=True)

# イメージファイルの作成
image = (
    modal.Image.debian_slim( python_version="3.11" )
    .apt_install("git", "ffmpeg", "libgl1-mesa-glx", "libglib2.0-0")

    # 3. 指定のPyTorchをインストール（extra_index_url を使用）
    .pip_install(  "torch", "torchvision", "torchaudio",
        extra_options="--upgrade --index-url https://download.pytorch.org/whl/cu130"
    )
    
    # 4. ComfyUIのクローンと依存パッケージのセットアップ
    .run_commands(
        "git clone https://github.com/Comfy-Org/ComfyUI /root/ComfyUI",
        "cd /root/ComfyUI && pip install -r requirements.txt",
    )
    
    # 5. Krea2 / 量子化処理等で必要なライブラリを追加
    .pip_install("bitsandbytes", "transformers", "accelerate")

    # volumeマウントのために以下のフォルダを削除
    .run_commands( "rm -rf /root/ComfyUI/models/*" )
    .run_commands( "rm -rf /root/ComfyUI/output/*" )
    .run_commands("ln -sf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime")   # JSTに設定
)

app = modal.App(name="comfyapp", image=image)

@app.function(
    max_containers=1,
    scaledown_window=900,
    timeout=1800,
    gpu="L4",
    cpu=2.0,
    memory=32768,
    volumes={ "/root/ComfyUI/models": model_volume,
              "/root/ComfyUI/output": output_volume }
)
def run_comfy():
    print("Starting ComfyUI...")
    cmd = [
        "python", "/root/ComfyUI/main.py",
        "--listen", "0.0.0.0",
        "--port", "8188",
    ]

    subprocess.Popen(cmd)

    with modal.forward(8188) as tunnel:
        print("⚡" * 40)
        print(f" 🟡 接続URL: {tunnel.url} 🟡")
        print("⚡" * 40)
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
