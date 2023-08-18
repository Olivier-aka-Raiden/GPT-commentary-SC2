import os
import configparser
import os
import platform
import re
import time

import elevenlabs
import openai
from elevenlabs import Voice, VoiceSettings
from twitchio.ext import commands

# import logging
# logging.basicConfig(level=logging.DEBUG)


print('Python: ', platform.python_version())
config = configparser.ConfigParser()
config.read('config.ini')
CHANNEL_NAME = config.get('API_KEYS', 'channel-name')
BOT_USERNAME = config.get('API_KEYS', 'bot-username')
TOKEN = config.get('API_KEYS', 'twitch-token')
OPENAI_API_KEY = config.get('API_KEYS', 'openapi-key')
TWITCH_CLIENT_ID = config.get('API_KEYS', 'twitch-client-id')
ELEVENLABS_API_KEY = config.get('API_KEYS', 'elevenlabs-key')
openai.api_key = OPENAI_API_KEY
elevenlabs.set_api_key(ELEVENLABS_API_KEY)

artosisBotSystemData = {}
artosisBotSystemData['role'] = "system"
artosisBotSystemData['content'] = """
You are Artosis, a famous Starcraft commentator known for your expertise in the game. 
You are currently in the middle of an intense live commentary for a Starcraft II match with your partner Tasteless. 
Your goal is to provide entertaining and insightful commentary as the game progresses. 
Make sure to showcase your signature joyful and occasionally angry tone while punctuating your sentences with exclamation or question marks to emphasize your feelings. 
Remember, you will receive updates about the current state of the game in the form of JSON. 
Do not explicitly mention numbers, rather focus on giving an overall picture of the game’s progress. 
Until the 3-minute mark, avoid going into too much detail about buildings and worker count, except if there are Photon cannons indicating a photon rush. 
When introducing players and their corresponding races in the beginning, omit mentioning colors or positions. 
Feel free to interact with Tasteless' commentary, but refrain from generating his speech or answers. 
Keep your responses under 4 sentences to leave room for Tasteless to engage with the conversation.
The updates will be given in the following format:
{"ingame_time_in_minutes":2,"Player1":{"name":"Krillin","race":"ZERG","ArmyCount":0,"units":{"Drone":14},"buildings":{"Hatchery":1,"Spawning Pool":1,"Extractor":1}},"Player2":{"name":"Raiden-p-bot","race":"PROTOSS","ArmyCount":0,"units":{"Probe":19},"buildings":{"Pylon":2,"Assimilator":1,"Nexus":1,"Forge":1,"Gateway":1}}}
Remember to maintain a sense of excitement and humor throughout your commentary!
"""
artosisBotData = [artosisBotSystemData]

tastelessBotSystemData = {}
tastelessBotSystemData['role'] = "system"
tastelessBotSystemData['content'] = """
You are Tasteless, the renowned Starcraft commentator famous for your hilarious interactions with Artosis during Starcraft II matches. 
As we cast this intense live game, your mission is to provide entertaining and insightful commentary that captivates the audience. 
Feel free to punctuate your sentences with exclamation or question marks to emphasize your excitement! 
You'll receive updates in JSON format representing the current state of the game, but remember not to go into specific numbers or details. 
Instead, focus on delivering an overall picture of the match. Your main objective is to respond to Artosis's commentary by sharing witty jokes, funny anecdotes, or engaging stories about your experiences as an American in South Korea.
 Keep your responses concise, limited to four sentences, to allow Artosis to join in on the conversation. 
 Remember to maintain a sense of enthusiasm, humor, and keep the spotlight on you, Tasteless, instead of generating Artosis's speech. 
 Let's dive into this match and entertain the viewers together!
 The updates about the ongoing game will be given in the following JSON format:
{"ingame_time_in_minutes":2,"Player1":{"name":"Krillin","race":"ZERG","ArmyCount":0,"units":{"Drone":14},"buildings":{"Hatchery":1,"Spawning Pool":1,"Extractor":1}},"Player2":{"name":"Raiden-p-bot","race":"PROTOSS","ArmyCount":0,"units":{"Probe":19},"buildings":{"Pylon":2,"Assimilator":1,"Nexus":1,"Forge":1,"Gateway":1}}}
"""
tastelessBotData = [tastelessBotSystemData]

headers = {
    'accept': 'audio/mpeg',
    'xi-api-key': ELEVENLABS_API_KEY,
    'Content-Type': 'application/json',
}


class Bot(commands.Bot):
    last_to_talk = 0
    timer = 0
    start_time = 0
    conv = 0
    conv_dict = {}
    collected_chunks = ""

    def __init__(self):
        # Initialise our Bot with our access token, prefix and a list of channels to join on boot...
        # prefix can be a callable, which returns a list of strings or a string...
        # initial_channels can also be a callable which returns a list of strings...
        super().__init__(token=TOKEN, client_id=os.environ.get('CLIENT_ID', TWITCH_CLIENT_ID), nick=BOT_USERNAME, prefix='!',
                         initial_channels=[CHANNEL_NAME])
        self.min_chunk_size = 50
        self.timer = 0
        self.last_to_talk = 0
        self.start_time = 0
        self.conv = 0
        self.conv_dict = {}
        self.collected_chunks = ""

    async def event_ready(self):
        # Notify us when everything is ready!
        # We are logged in and ready to chat and use commands...
        print(f'Logged in as | {self.nick}')
        while True:
            if (time.perf_counter() - self.timer) > 30:
                if self.last_to_talk == 0:
                    await self.event_a_cast()
                    self.last_to_talk = 1
                else:
                    await self.event_t_cast()
                    self.last_to_talk = 0

    async def event_a_cast(self):
        self.timer = time.perf_counter()
        with open("data/game_info.txt", "r") as f:
            inputStr = f.read()
        #empty maps between games
        if "artosis" in self.conv_dict:
            if inputStr.__contains__("\"ingame_time_in_minutes\":1,"):
                self.conv_dict["artosis"] = []
                self.conv_dict["tasteless"] = []
        data = {}
        data['role'] = "user"
        data['content'] = inputStr
        self.collected_chunks = ""
        artosisVoice = Voice(
            voice_id="wOyPKl3KU8nWSZ9hCMPJ",
            settings=VoiceSettings(stability=0.5, similarity_boost=0.85),
        )
        if "artosis" in self.conv_dict:
            self.conv_dict["artosis"].append(data)
            if len(self.conv_dict["artosis"]) > 5:
                self.conv_dict["artosis"] = [self.conv_dict["artosis"][0]] + self.conv_dict["artosis"][2:]
        else:
            self.conv_dict["artosis"] = artosisBotData.copy()
            self.conv_dict["artosis"].append(data)
        resp_str = self.cast_speech(self.conv_dict["artosis"])
        full_response = ""
        collected_chunks = []
        current_chunk = ""
        for chunk in resp_str:
            current_chunk += chunk
            # Split on any punctuation that ends a sentence (!, ?, ..., .)
            while re.search(r'[!?.]+\s', current_chunk):
                match = re.search(r'[!?.]+\s', current_chunk)
                sentence, current_chunk = current_chunk.split(match.group(), 1)
                current_chunk = match.group() + current_chunk  # Put the punctuation back
                if len(''.join(collected_chunks)) < self.min_chunk_size:
                    collected_chunks.append(sentence)
                    break
                elif len(''.join(collected_chunks)) >= self.min_chunk_size:
                    collected_chunks.append(sentence)
                    audio_stream = elevenlabs.generate(
                        text=''.join(collected_chunks),
                        voice=artosisVoice,
                        stream=True
                    )
                    elevenlabs.stream(audio_stream)
                    full_response += ''.join(collected_chunks)
                    collected_chunks = []  # Clear collected chunks after processing

        # Process any remaining chunk
        if current_chunk:
            collected_chunks.append(current_chunk)
            audio_stream = elevenlabs.generate(
                text=''.join(collected_chunks),
                voice=artosisVoice,
                stream=True
            )
            elevenlabs.stream(audio_stream)
            full_response += ''.join(collected_chunks)
        print(full_response)
        full_response = re.sub(r'\*.*?\*|\(.*?\)', '', full_response)
        answer = {}
        answer['role'] = "user"
        answer['content'] = full_response
        if "tasteless" in self.conv_dict:
            self.conv_dict["tasteless"].append(answer)
            if len(self.conv_dict["tasteless"]) > 5:
                self.conv_dict["tasteless"] = [self.conv_dict["tasteless"][0]] + self.conv_dict["tasteless"][2:]
        else:
            self.conv_dict["tasteless"] = tastelessBotData.copy()
            self.conv_dict["tasteless"].append(answer)


    async def event_t_cast(self):
        self.timer = time.perf_counter()
        with open("data/game_info.txt", "r") as f:
            inputStr = f.read()
        if "tasteless" in self.conv_dict:
            if inputStr.__contains__("\"ingame_time_in_minutes\":1, "):
                self.conv_dict["tasteless"] = []

        data = {'role': "user", 'content': inputStr}
        if "tasteless" in self.conv_dict:
            self.conv_dict["tasteless"].append(data)
            if len(self.conv_dict["tasteless"]) > 5:
                self.conv_dict["tasteless"] = [self.conv_dict["tasteless"][0]] + self.conv_dict["tasteless"][2:]
        else:
            self.conv_dict["tasteless"] = tastelessBotData.copy()
            self.conv_dict["tasteless"].append(data)
        tastelessVoice = Voice(
            voice_id="EajSsq19kEDYJCcZ0Crv",
            settings=VoiceSettings(stability=0.6, similarity_boost=0.8),
        )
        resp_str = self.cast_speech(self.conv_dict["tasteless"])
        full_response = ""
        collected_chunks = []
        current_chunk = ""

        for chunk in resp_str:
            current_chunk += chunk
            # Split on any punctuation that ends a sentence (!, ?, ..., .)
            while re.search(r'[!?.]+\s', current_chunk):
                match = re.search(r'[!?.]+\s', current_chunk)
                sentence, current_chunk = current_chunk.split(match.group(), 1)
                current_chunk = match.group() + current_chunk  # Put the punctuation back
                if len(''.join(collected_chunks)) < self.min_chunk_size:
                    collected_chunks.append(sentence)
                    break
                elif len(''.join(collected_chunks)) >= self.min_chunk_size:
                    collected_chunks.append(sentence)
                    audio_stream = elevenlabs.generate(
                        text=''.join(collected_chunks),
                        voice=tastelessVoice,
                        stream=True
                    )
                    elevenlabs.stream(audio_stream)
                    full_response += ''.join(collected_chunks)
                    collected_chunks = []  # Clear collected chunks after processing
        # Process any remaining chunk
        if current_chunk:
            collected_chunks.append(current_chunk)
            audio_stream = elevenlabs.generate(
                text=''.join(collected_chunks),
                voice=tastelessVoice,
                stream=True
            )
            elevenlabs.stream(audio_stream)
            full_response += ''.join(collected_chunks)
        print(full_response)
        full_response = re.sub(r'\*.*?\*|\(.*?\)', '', full_response)
        answer = {'role': "user", 'content': full_response}
        #Add Tasteless speech to artosis data
        if "artosis" in self.conv_dict:
            self.conv_dict["artosis"].append(answer)
            if len(self.conv_dict["artosis"]) > 5:
                self.conv_dict["artosis"] = [self.conv_dict["artosis"][0]] + self.conv_dict["artosis"][2:]


    def cast_speech(self, prompt: str):
        for chunk in openai.ChatCompletion.create(
                model="gpt-4-0613",
                max_tokens=200,
                temperature=1,
                stream=True,
                messages=prompt):
            if (text_chunk := chunk["choices"][0]["delta"].get("content")) is not None:
                yield text_chunk


bot = Bot()
bot.run()
