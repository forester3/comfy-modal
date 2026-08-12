# ## Overview
#
# Quick snippet showing how to connect to a Jupyter notebook server running inside a Modal container,
# especially useful for exploring the contents of Modal Volumes.
# This uses [Modal Tunnels](https://modal.com/docs/guide/tunnels#tunnels-beta)
# to create a tunnel between the running Jupyter instance and the internet.
#
# If you want to your Jupyter notebook to run _locally_ and execute remote Modal Functions in certain cells, see the `basic.ipynb` example :)

import os
import subprocess
import time
import modal

deb_file = "megacmd-Debian_12_amd64.deb"
deb_url = f"https://mega.nz/linux/repo/Debian_12/amd64/{deb_file}"
theme_config_dir = "/root/.jupyter/lab/user-settings/@jupyterlab/apputils-extension"

app = modal.App(
    "jupyter-inside-modal",
    image=modal.Image.debian_slim(python_version="3.12")
        .apt_install("bash", "git", "wget", "aria2")
        .uv_pip_install("jupyterlab", "ipywidgets")
        .env({"SHELL": "/bin/bash"})
        .run_commands(  f"wget -q -O {deb_file} {deb_url}", 
                        f"apt install -y ./{deb_file}",
                        f"rm -f {deb_file}")
        .run_commands(  f"mkdir -p '{theme_config_dir}'",
                    # 2. ダークテーマを指定した JSON ファイルを作成
                        f'echo \'{{"theme": "JupyterLab Dark"}}\' > "{theme_config_dir}/themes.jupyterlab-settings"')
        .run_commands("cd /root && git clone --depth=1 https://github.com/forester3/comfy-work-steps.git # {sha}")
)


output_vol = modal.Volume.from_name( "comfy-output", create_if_missing=True )
models_vol = modal.Volume.from_name( "comfy-models", create_if_missing=True )

JUPYTER_TOKEN = "zero"  # Change me to something non-guessable!


# This is all that's needed to create a long-lived Jupyter server process in Modal
# that you can access in your Browser through a secure network tunnel.
# This can be useful when you want to interactively engage with Volume contents
# without having to download it to your host computer.


@app.function(max_containers=1,
              volumes={"/root/ComfyUI/output": output_vol, 
                       "/root/ComfyUI/models": models_vol, }, 
              secrets=[modal.Secret.from_dotenv()],
              timeout=1_500)
def run_jupyter(timeout: int):
    jupyter_port = 8888
    with modal.forward(jupyter_port) as tunnel:
        jupyter_process = subprocess.Popen(
            [
                "jupyter", "lab",
                "--no-browser", "--allow-root", "--ip=0.0.0.0",
                f"--port={jupyter_port}",
                "--NotebookApp.allow_origin='*'",
                "--NotebookApp.allow_remote_access=1",
                "--notebook-dir=/root",
            ],
            env={**os.environ, "JUPYTER_TOKEN": JUPYTER_TOKEN},
        )

        print("⚡" * 40)
        print(f"JupyterLab 🔌 {tunnel.url}")
        print("⚡" * 40)

        try:
            end_time = time.time() + timeout
            while time.time() < end_time:
                time.sleep(5)
            print(f"Reached end of {timeout} second timeout period. Exiting...")
        except KeyboardInterrupt:
            print("Exiting...")
        finally:
            jupyter_process.kill()


@app.local_entrypoint()
def main(timeout: int = 10_000):
    # Run the Jupyter server
    run_jupyter.remote(timeout=timeout)
