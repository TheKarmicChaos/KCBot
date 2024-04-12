from lib import *
from trl import SFTTrainer
import transformers

#model = './tmp_trainer/checkpoint-570'         # replace this with the dir of the checkpoint/model you want to chat with
model = transformers.AutoModelForCausalLM.from_pretrained("facebook/opt-350m")
tokenizer = transformers.AutoTokenizer.from_pretrained("facebook/opt-350m")

generator = transformers.pipeline(
        task = 'text-generation',
        model = model,
        tokenizer = tokenizer,
        max_new_tokens = 100,   # Limit the amount of new tokens the AI can generate to just 100.
        device = "cpu",          # change this to an int to use the GPU of that ordinal rank instead (0 if you have one GPU)
        #exponential_decay_length_penalty = (20, 1.3)
)

def generate_message(inputText : str) -> str:
        name = getNames()[str(getConfig()["userToImpersonateID"])]
        prompt = f"You are {name} in a chat room with some friends. You chat unfiltered, and saying rude things, cracking jokes, and swearing are encouraged. Send the next message as {name}."

        text = f"""### Instruction:
{prompt}

### Chat:
{inputText}
"""
        completedText = generator(
                text_inputs = text,
                return_full_text = False,       # Only return the added text
                do_sample = True,
                temperature = 0.5)
        return completedText[0]['generated_text']

# Replace the input text with whatever input you want to model to respond to.
print(generate_message("""Tom: My computer is so fucking hot right now.
Jeremy: cook an egg on it
Jeremy: but dont eat it
they put something in it. to make you forget
Tom: don't train on the degeneral data
they put something in it
to make you forget
Jeremy: TRUE
Tom: 1st epoch is finished and now I can peek into the model for fun. Apparently "Paul" is the 1206th ranked word in the AI's vocabulary
Rhett: What's the 1205th ranked word?"""))