from workflow import remake_workflow
from generate import generate_image, wait4completion

MODEL_NAME = "gonzalomoKrea2_v30"
SUFFIX = "-gz"
PROMPTS = ["""
photo of a Japanese woman, natural daylight, looking at camera
""","""
a woman sitting near a window, dark room, single side light
""","""
a girl wearing headphones, holding a coffee cup, messy hair
"""]
SEEDS =[    1234567890, 2345678901, 3456789012, 4567890123,
            5678901234, 6789012345, 7890123456, 8901234567  ]

def procedure():

    for prompt in PROMPTS:
        for seed in SEEDS:
            workflow = remake_workflow( MODEL_NAME, positive=prompt, seed=seed, suffix=SUFFIX )
            result = generate_image( workflow )
            wait4completion( result["prompt_id"] )

    return
