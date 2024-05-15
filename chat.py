from lib import *
from trl import SFTTrainer
import transformers

class ChatClient(dc.Client):
    """Discord bot client for sending and responding to chat messages.
    When activated with initBot() it will respond to messages starting with "/kc"
    in the the channels specified in config.json.
    """
    config = getConfig()
    names = getNames()
    guildID = config["guildID"]
    channelIDs = config["channelIDs"]
    is_generating = False
    
    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print(f'Guild: "{self.get_guild(self.guildID)}"')
        print('------')
        print(f'Chatbot enabled in the following channels:')
        for channel in self.channelIDs:
            print(self.get_channel(channel))
        print('------')

    async def on_message(self, message: dc.Message):
        # we do not want the bot to reply to itself
        if message.author.id == self.user.id:
            return

        if message.content.startswith('/kc'):
            
            # we want the bot to ignore messages if it is currently generating a response
            if self.is_generating:
                return
            
            self.is_generating = True
            async with message.channel.typing(): # start typing to let users know a response is coming
                
                # Get the recent message history, cleaned and formatted
                msgHistory = []
                async for msg in message.channel.history(limit=10):
                    messageContent = cleanMsg(msg.content, str(msg.author.id), self.names, self.config)
                    if messageContent != "":
                        msgHistory.append(formatMsg(messageContent, str(msg.author.id), self.names, self.config))
                # combine the messages into a single input string
                msgHistoryStr = "\n".join(reversed(msgHistory))
                responses = generate_message(msgHistoryStr) # Array of generated responses
                print(msgHistoryStr + "\n")
                testprint(responses)
                await message.reply(responses[0], mention_author=True) # reply with the first of the generated response
            self.is_generating = False

# Code for running chat bot
def runChatBot():
    intents = dc.Intents.default()
    intents.message_content = True

    client = ChatClient(intents=intents)
    initBot(client)


# ----------------------------------------------------------------------------------


model = 'model.bin'         # replace this with the dir of the checkpoint/model you want to chat with
#model = transformers.AutoModelForCausalLM.from_pretrained("facebook/opt-350m")
tokenizer = transformers.AutoTokenizer.from_pretrained("facebook/opt-350m")

generator = transformers.pipeline(
        task = 'text-generation',
        model = model,
        tokenizer = tokenizer,
        device = "cpu",         # change this to an int to use the GPU of that ordinal rank instead (0 if you have one GPU)
        max_new_tokens = 200,   # Hard limit to the amount of new tokens the AI can generate.
        exponential_decay_length_penalty = (20, 1.05),  # Increase penalty by given exponent for each new token generated after 20th token (to keep messages short)
)

def generate_message(inputText : str) -> str:
        name = getNames()[str(getConfig()["userToImpersonateID"])]
        prompt = f"You are {name} in a chat room with some friends. You chat unfiltered, and saying rude things, cracking jokes, and swearing are encouraged."

        text = f"""### Instruction:
{prompt}

### Input:
{inputText}

### Response:
"""
        completedText = generator(
                text_inputs = text,
                return_full_text = False,       # Only return the added text
                do_sample = True,               # Required for AI to keep track of context when generating text.
                num_return_sequences = 10,      # Number of responses generated
                temperature = 0.75,             # Value from 0-1. Lower temperature gives more random but less intelligible results, while higher is more predictable.
                )
        return [x['generated_text'] for x in completedText]

def testprint(msgs : list[str]):
    for msg in msgs:
        print(msg + "\n\n")

testmsg1 = """Tom: My computer is so fucking hot right now.
Jeremy: cook an egg on it
Jeremy: but dont eat it
they put something in it. to make you forget
Tom: don't train on the degeneral data
they put something in it
to make you forget
Jeremy: TRUE
Tom: 1st epoch is finished and now I can peek into the model for fun. Apparently "Paul" is the 1206th ranked word in the AI's vocabulary
Rhett: What's the 1205th ranked word?"""

testmsg2 = """Jeremy: i am going to write a program to manually go through all of my messages and append the word badger at the end to fuck with the results badger
Tom: I can just clean the data if you do that badger
Jeremy: lol badger
Tom: oh and yes, this does mean if you edit past messages it WILL fuck with the results, but as long as you don't do stuff like append badger to every message, edits wont really make a big impact. badger
Tom: Oh yeah, I don't think I mentioned this before: The AI will literally believe it is me. The way I'm training it and the way I intend to implement it will result in it thinking that messages I send were actually sent by it. So basically it's gonna be fucking impossible for me to interact with it unless I hardcode something that makes it think I'm one of you guys.
Tom: badger
Rhett: counter point, just make it think that it has schizophrenia. badger"""



# Use this line for testing. Replace the input text with whatever input you want to model to respond to.
#testprint(generate_message(testmsg2))

# Use this line if you want the bot to run in discord and respond to messages
runChatBot()