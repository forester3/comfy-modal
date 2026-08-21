import subprocess
import time
import requests
import modal

model_volume = modal.Volume.from_name( "comfy-models", create_if_missing=True )
output_volume = modal.Volume.from_name( "comfy-output", create_if_missing=True )

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install( "git", "ffmpeg", "libgl1-mesa-glx", "libglib2.0-0" )
    .pip_install( "torch", "torchvision", "torchaudio",
        extra_options=( "--upgrade " "--index-url https://download.pytorch.org/whl/cu130" )
    )
    .run_commands(
        "git clone https://github.com/Comfy-Org/ComfyUI /root/ComfyUI",
        "cd /root/ComfyUI && pip install -r requirements.txt",
    )
    .pip_install( "bitsandbytes", "transformers", "accelerate" )
    .run_commands(
        "rm -rf /root/ComfyUI/models/* /root/ComfyUI/output/*",
        "ln -sf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime"
    )
    .pip_install("websocket-client")                                # for API 
    .add_local_dir( "workflow", remote_path="/root/workflow", )     # local系は最後に
    .add_local_python_source( "generate", "workflow", "procedure" )
)

from procedure import procedure

app = modal.App( name="comfy-api", image=image )

@app.function(
    max_containers=1,
    scaledown_window=1200,
    timeout=7200,
    gpu="L4",
    cpu=2.0,
    memory=32768,
    volumes={   "/root/ComfyUI/models": model_volume,
                "/root/ComfyUI/output": output_volume,  }
)
def run_comfy_api():

    process = subprocess.Popen([    "python", "/root/ComfyUI/main.py",
                                    "--listen", "127.0.0.1", "--port", "8188", ])
    print("⏳ Waiting for ComfyUI...")

    for i in range(120):
        try:
            r = requests.get( "http://127.0.0.1:8188/system_stats", timeout=2 )

            if r.status_code == 200:
                print("🟢 ComfyUI is ready!")
                break

        except requests.RequestException:
            pass

        time.sleep(1)

    else:
        raise RuntimeError("❌ ComfyUI did not start")

    # API確認
    r = requests.get( "http://127.0.0.1:8188/system_stats" )
    print("ComfyUI system stats:")
    print(r.json())

    try:
        procedure()

    finally:
        print("🏁 ComfyUI will be closed...")
        process.terminate()
        process.wait()
