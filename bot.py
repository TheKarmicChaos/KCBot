# Kaycee bot requires the 'message_content' intent to be enabled.

import discord as dc
import json

def initBot():
    """Sets up bot using config.json and connects it to your server so you can use it."""
    config = {}
    # Read config from file
    with open('config.json', 'r') as f:
        config = json.loads(f.read())
        f.close()

    try: # Try to construct config dict from the read file
        intents = dc.Intents.default()
        intents.message_content = True

        client = MyClient(intents=intents)
        client.run(config["botToken"])
    except:
        print("Could not load config.json properly. Perhaps you forgot to replace the placeholders?")


class MyClient(dc.Client):
    """Run bot with ScrapeClient to enable scraping of messages.

    Args:
        dc (_type_): _description_
    """
    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

    async def on_message(self, message):
        # we do not want the bot to reply to itself
        if message.author.id == self.user.id:
            return

        if message.content.startswith('/kc'):
            await message.reply('Hello!', mention_author=True)

initBot()