import json
import random 
from datetime import datetime

WORKFLOW_FILE = "/root/workflow/260817-bf_00021_.json"

def remake_workflow( model_name:str, positive=None, seed=None, suffix=None):
    with open(WORKFLOW_FILE, "r", encoding="utf-8") as f:
        workflow = json.load(f)

    for node in workflow.values():
        if isinstance(node, dict):
            inputs = node.get("inputs", {})

            if node.get("class_type") == "SaveImage":       # %date:yyMMdd%代用
                if "filename_prefix" in inputs:
                    inputs["filename_prefix"] = datetime.now().strftime("%y%m%d") + suffix

            if node.get("class_type") == "UNETLoader":      # Krea2 diffusion_models
                if model_name is not None:
                    inputs["unet_name"] = model_name + ".safetensors"

            if node.get("class_type") == "CLIPTextEncode":
                if "text" in inputs:
                    if positive is not None:
                        inputs["text"] = positive   # ポジティブプロンプト

            if node.get("class_type") == "KSampler":         # Seed
                if "seed" in inputs and seed is not None:
                    if seed == -1:
                        inputs["seed"] = random.randint(0, 10**15 - 1) #Number.MAX_SAFE_INTEGER対応
                    elif seed == -2:
                        inputs["seed"] = random.randint(0, 2**64 - 1)
                    else:
                        inputs["seed"] = seed

    return( workflow )

