# __**KCBot**__
Kaycee is an AI language model trained on my Discord message history, allowing it to respond to messages as I would. Included in this repo are all files written and used for this project, but the data I scraped and the AI data post-training have been excluded for privacy reasons. This repo can be used to create another Kaycee bot trained off of someone else's Discord message history, the instructions for which have been included in the setup below.

All parties in the server from which the message history data have given consent for me to use said data for this project, and will be asked again if I decide to update Kaycee with newer data.

## __Setup:__
* Install all required Python packages (listed below)
* Create a Discord bot with message content intent enabled and add it to your server.
* Download KCBot and put the directory anywhere you want on your system.
* Open "KCBot/config.json" and replace the "xxxxx" placeholders with the appropriate information (bot authentication token, ID of your discord server, IDs of each channel that the bot can scrape/chat in, etc).
* Open "KCBot/names.json" and list all ID/name pairs you wish to replace in the training data. Occurances of these IDs in the dataset will be replaced by the corresponding string listed in this file. All @mentions, #channel mentions, @role mentions, etc not listed here will instead be completely deleted from the data.
* Run scrape.py to have your bot collect data.
* Run train.py and wait until it finishes (this may take a few days). loss should get closer to 0 each epoch if the training is going well. You can use chat.py to test checkpoints by giving them an input to respond to.
* Run chat.py whenever you want the bot to be active! It will respond to messages starting with "/kc".


## __Required package installations:__
* [discord.py][https://discordpy.readthedocs.io/en/stable/intro.html]
* [trl][https://huggingface.co/docs/trl/main/en/installation]


## __Credit:__
Early on, I found [this post from Timo][https://gotimo2.github.io/posts/training-an-llm-on-150k-discord-messages/] about them working on a similar project. Although I didn't use any of their code, this post was invaluable and deserves a credit on this project.
