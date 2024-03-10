# Kaycee bot requires the 'message_content' intent to be enabled.

import discord as dc
import json


def getConfig():
    """Reads config from file and returns a config dict"""
    config = {}
    with open('config.json', 'r') as f:
        config = json.loads(f.read())
        f.close()
    # convert IDs to ints
    config['guildID'] = int(config['guildID'])
    channelIDs = []
    for channel in config['channelIDs']:
        channelIDs.append(int(channel))
    config['channelIDs'] = channelIDs
    return config


def initBot(client):
    """Sets up a bot client using config.json and connects it to your server so you can use it.
    
    Args:
        client (Client): Discord client connection object with the corresponding code & intents for the desired behavior of the bot.
    """
    
    config = getConfig()
    try:
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