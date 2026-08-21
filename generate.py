import json
import uuid

from workflow import remake_workflow

COMFY_URL = "http://127.0.0.1:8188"
client_id = str(uuid.uuid4())

def generate_image( workflow ):

    payload = {
        "prompt": workflow,
        "client_id": client_id,
    }
    response = requests.post( f"{COMFY_URL}/prompt", json=payload )
    response.raise_for_status()
    result = response.json()

    print("🆔 Prompt ID:", result["prompt_id"])
    return result


def wait4completion( prompt_id ):
    ws = websocket.create_connection( f"ws://127.0.0.1:8188/ws?clientId={client_id}" )

    try:
        while True:
            message = ws.recv()

            if not message:
                continue

            data = json.loads(message)                          # ComfyUIのWebSocketメッセージはJSON

            # 実行中のノード情報
            if data["type"] == "executing":
                node = data["data"].get("node")
                current_prompt_id = data["data"].get("prompt_id")

                if ( current_prompt_id == prompt_id and node is None ): # 自分のprompt_idで、nodeがNoneになったら完了
                    print("🎨 completed!!")
                    return
    finally:
        ws.close()   


if __name__ == "__main__":
    generate_image()