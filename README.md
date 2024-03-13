# __**KCBot**__
Kaycee is an AI language model trained on my Discord message history, allowing it to respond to messages as I would. Included in this repo are all files written and used for this project, but the data I scraped and the AI data post-training have been excluded for privacy reasons. This repo can be used to create another Kaycee bot trained off of someone else's Discord message history, the instructions for which have been included in the setup below.

All parties in the server from which the message history data have given consent for me to use said data for this project, and will be asked again if I decide to update Kaycee with newer data.

## __Setup:__
* Install all required Python modules (listed below)
* Create a Discord bot with message content intent enabled.
* Download KCBot and put the directory anywhere you want on your system. It will create a separate KCBot_db directory at root for training data.
* In the KCBot directory, open the file named "config.json" and replace the "xxxxx" placeholders with your bot's authentication token, the ID of your discord server, and the IDs of each channel in the server that the bot can scrape/chat in.

## __Required modules:__
* os
* sqlite3
* json
* discord.py