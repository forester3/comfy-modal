import subprocess
import time
import requests
import modal
from pathlib import Path
# local module
from procedure import procedure    

COMFY_PORT = 8188
TIMEOUT = 7200
NODES = [   "https://github.com/ltdrdata/ComfyUI-Manager.git",
            "https://github.com/MoonGoblinDev/Civicomfy.git",
            "https://github.com/ltdrdata/ComfyUI-Impact-Pack.git",
            "https://github.com/ltdrdata/ComfyUI-Impact-Subpack.git",
            "https://github.com/ssitu/ComfyUI_UltimateSDUpscale.git",
            "https://github.com/1038lab/ComfyUI-QwenVL.git",
            "https://github.com/ClownsharkBatwing/RES4LYF.git",
            "https://github.com/blue-pen5805/ComfyUI-krea2-negpip.git" ]
COMFY_STATS = "http://127.0.0.1:8188/system_stats"

model_volume = modal.Volume.from_name( "comfy-models", create_if_missing=True )
output_volume = modal.Volume.from_name( "comfy-output", create_if_missing=True )

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install( "git", "ffmpeg", "libgl1-mesa-glx", "libglib2.0-0" )
    .pip_install( "torch", "torchvision", "torchaudio",
        extra_options=( "--upgrade " "--index-url https://download.pytorch.org/whl/cu130" )
    )
    .run_commands(
        "pip install --upgrade pip",
        "git clone https://github.com/Comfy-Org/ComfyUI /root/ComfyUI",
        "cd /root/ComfyUI && pip install -r requirements.txt",
    )
    .run_commands(
        *[f"cd /root/ComfyUI/custom_nodes && git clone {node}" for node in NODES],
    )
    .run_commands(
        "pip install -r /root/ComfyUI/custom_nodes/ComfyUI-Impact-Pack/requirements.txt",
        "pip install -r /root/ComfyUI/custom_nodes/ComfyUI-Impact-Subpack/requirements.txt",
        "pip install -r /root/ComfyUI/custom_nodes/RES4LYF/requirements.txt",
    )
    .pip_install( "bitsandbytes", "transformers", "accelerate", "websocket-client" )
                                                                # for API
    .run_commands(
        "rm -rf /root/ComfyUI/models/* /root/ComfyUI/output/*",
        "ln -sf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime"
    )
    .add_local_dir( "workflow", remote_path="/root/workflow", )     # local系は最後に
    .add_local_python_source( "generate", "workflow", "procedure" ) # API作画モジュール
)


app = modal.App( name="comfy-modal", image=image )

@app.function(
    max_containers=1,
    scaledown_window=1200,
    timeout=TIMEOUT,
    gpu=["L4", "A10G"], cpu=2.0, memory=32768,
    volumes={   "/root/ComfyUI/models": model_volume,
                "/root/ComfyUI/output": output_volume,  }
)

def run_comfy( api_mode: bool  ):
    print("🔴 Starting ComfyUI...")
    process = subprocess.Popen([    "python", "/root/ComfyUI/main.py",
                                    "--listen", "0.0.0.0", "--port", "8188", ])
    start_time = time.time()
    for i in range(120):
        try:
            r = requests.get( COMFY_STATS, timeout=2 )
            if r.status_code == 200:
                print("🟢 ComfyUI is ready!")
                break

        except requests.RequestException:
            pass

        time.sleep(1)
    else:
        raise RuntimeError("❌ ComfyUI did not start")

    r = requests.get( COMFY_STATS )
    print("ComfyUI system stats:")
    print(r.json())

    if api_mode == False:
        print( "WebUI用のトンネルを開きます。")
        with modal.forward( COMFY_PORT ) as tunnel:
            print("⚡" * 40)
            print(f"⚡ 接続URL: \033[0m{tunnel.url} \033[0m⚡")
        
            try:
                while True:
                    remaining = max(0, int(TIMEOUT + start_time - time.time()))
                    print(f"⚠️⌚ \033[0m Timeout まで残り: {remaining}\033[0m")
                    time.sleep(300)
                
            except KeyboardInterrupt:
                pass
    else:
        print( "APIモードで、作画(procedure.py)を実行します...")
        try:
            procedure()

        finally:
            print("🏁 ComfyUI will be closed...")
            process.terminate()
            process.wait()

@app.local_entrypoint()
def main(api: bool = False):  # --api を付けるだけで True になる
    # クラウドの関数を呼び出し、値を引き渡す
    run_comfy.remote(api_mode=api)
