# __**KCBot**__
Kaycee is an AI large language model trained on my Discord message history, allowing it to respond to messages as I would. Included in this repo are all files written and used for this project, but the data I scraped and the AI data post-training have been excluded for privacy reasons. This repo can be used to create another Kaycee bot trained off of someone else's Discord message history, the instructions for which have been included in the setup below.

Early on when making this, I found [this post from Timo](https://gotimo2.github.io/posts/training-an-llm-on-150k-discord-messages/) about them working on a similar project, which inspired several of my own decisions when making this, most notably the format and prompt for the training data.

_All parties in the server from which the message history data have given consent for me to use said data for this project, and will be asked again if I decide to update Kaycee with newer data._

## __Setup:__
* Install all required Python packages (listed below)
* Create a new Discord bot with message content intent enabled and add it to your server.
* Download KCBot and put the directory anywhere you want.
* Open ***KCBot/config.json*** and replace the "xxxxx" placeholders with the appropriate information (bot auth token, ID of your server, IDs of each channel that the bot can scrape/chat in, etc).
* Open ***KCBot/names.json*** and list all ID/name pairs you wish to replace in the training data. Occurances of these IDs in the dataset will be replaced by the corresponding string listed in this file. All _@mentions_, _#channel_ mentions, _@role_ mentions, etc not listed will instead be completely deleted from the dataset.
* Run ***scrape.py*** to have your bot scrape the message history data.
* Run ***train.py*** to train the AI model and wait until it finishes, which may take a few days. "loss" and "eval_loss" should get closer to 0 each epoch if the training is going well.
* Run ***chat.py*** whenever you want the bot to be active! It will respond to messages starting with "/kc".


## __Required package installations:__
* [discord.py](https://discordpy.readthedocs.io/en/stable/intro.html)
* [trl](https://huggingface.co/docs/trl/main/en/installation)


## __Liscence:__
 Copyright 2024 Thomas "KarmicChaos" Prezioso

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
