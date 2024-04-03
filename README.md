# __**KCBot**__
Kaycee is an AI language model trained on my Discord message history, allowing it to respond to messages as I would. Included in this repo are all files written and used for this project, but the data I scraped and the AI data post-training have been excluded for privacy reasons. This repo can be used to create another Kaycee bot trained off of someone else's Discord message history, the instructions for which have been included in the setup below.

All parties in the server from which the message history data have given consent for me to use said data for this project, and will be asked again if I decide to update Kaycee with newer data.

## __Setup:__
* Install all required Python modules and other installations (listed below)
* Create a Discord bot with message content intent enabled.
* Download KCBot and put the directory anywhere you want on your system. All directories and files used by the program will be locally saved to this location.
* In the KCBot directory, open the file named "config.json" and replace the "xxxxx" placeholders with your bot's authentication token, the ID of your discord server, and the IDs of each channel in the server that the bot can scrape/chat in.
* Also open the file named "names.json" and list all ID/name pairs you wish to replace in the training data. Occurances of these IDs in the dataset will be replaced by the corresponding string listed in this file. All @mentions, #channel mentions, @role mentions, etc not listed here will instead be completely deleted from the data.

## __Required installations:__
* [discord.py][https://discordpy.readthedocs.io/en/stable/intro.html]
* [trl][https://huggingface.co/docs/trl/main/en/installation]