import subprocess
import time
import modal
from pathlib import Path

COMFY_PORT = 8188
TIMEOUT = 7200
# 使用するカスタムノードのリスト
NODES = [ "https://github.com/MoonGoblinDev/Civicomfy.git",  ]

# Volumeの作成
model_volume = modal.Volume.from_name("comfy-models", create_if_missing=True)
output_volume = modal.Volume.from_name("comfy-output", create_if_missing=True)

# イメージファイルの作成
image = (
    modal.Image.debian_slim( python_version="3.11" )
    .apt_install("git", "ffmpeg", "libgl1-mesa-glx", "libglib2.0-0")
    .pip_install(  "torch", "torchvision", "torchaudio",
        extra_options="--upgrade --index-url https://download.pytorch.org/whl/cu130"
    )
    .run_commands(
        "git clone https://github.com/Comfy-Org/ComfyUI /root/ComfyUI",
        "cd /root/ComfyUI && pip install -r requirements.txt",
    )
    .pip_install("bitsandbytes", "transformers", "accelerate")              # 量子化処理等で必要なライブラリを追加
    .run_commands( "rm -rf /root/ComfyUI/models/* /root/ComfyUI/output/*" ) # volumeマウントのためにフォルダを削除
    .run_commands("ln -sf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime")   # JSTに設定
)

app = modal.App(name="comfyapp", image=image)

@app.function(
    max_containers=1,
    scaledown_window=1200,
    timeout=TIMEOUT,
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
    start_time = time.time()
    
    with modal.forward( COMFY_PORT ) as tunnel:
        print("⚡" * 40)
        print(f"⚡ \033[0m接続URL: {tunnel.url} \033[0m⚡")
        
        try:
            while True:
                remaining = max(0, int(TIMEOUT + start_time - time.time()))
                print(f"⚠️⌚ \033[0m Timeout まで残り: {remaining}\033[0m")
                time.sleep(300)
                
        except KeyboardInterrupt:
            pass
