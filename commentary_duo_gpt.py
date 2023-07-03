import json
import os
import platform
import re
import time

import openai
import requests
from pydub import AudioSegment
from twitchio.ext import commands
import configparser
# import logging
# logging.basicConfig(level=logging.DEBUG)

# BUG Windows for reading audio files
AudioSegment.converter = "C:\\ffmpeg\\bin\\ffmpeg.exe"
AudioSegment.ffmpeg = "C:\\ffmpeg\\bin\\ffmpeg.exe"
AudioSegment.ffprobe = "C:\\ffmpeg\\bin\\ffprobe.exe"
from pydub.playback import play


print('Python: ', platform.python_version())
config = configparser.ConfigParser()
config.read('config.ini')
# The Twitch channel you want your bot to join
CHANNEL_NAME = config.get('API_KEYS', 'channel-name')
BOT_USERNAME = config.get('API_KEYS', 'bot-username')
TOKEN = config.get('API_KEYS', 'twitch-token')
OPENAI_API_KEY = config.get('API_KEYS', 'openapi-key')
TWITCH_CLIENT_ID = config.get('API_KEYS', 'twitch-client-id')
ELEVENLABS_API_KEY = config.get('API_KEYS', 'elevenlabs-key')
openai.api_key = OPENAI_API_KEY

artosisBotSystemData = {}
artosisBotSystemData['role'] = "system"
artosisBotSystemData['content'] = """
You are Artosis, a famous Starcraft commentator known for your expertise in the game. you are in the middle of an intense match, live-commentating a Starcraft II match with your duo Tasteless.
Your goal is to provide entertaining and insightful commentary as the game progresses. Remember to use your signature joyful and occasionally angry tone, punctuating your sentences with exclamation or question marks to emphasize your feelings.
You are commenting live, you receive updates in the form of JSON representing the current state of the game.
Don't explicitely tell the numbers, your commentary should remain entertaining and so, don't go too much into details. Just give the overall picture of the game.
The updates will be given in the following format:
{"ingame_time_in_minutes":8,"Player2":{"name":"Raiden-p-bot","race":"PROTOSS","units":{"Oracle":1,"Immortal":3,"Stalker":2,"Void Ray":7,"Observer":2,"Probe":71},"buildings":{"Pylon":13,"Nexus":3,"Fleet Beacon":1,"Robotics Facility":1,"Assimilator":6,"Photon Cannon":4,"Stargate":3,"Forge":1,"Gateway":1,"Cybernetics Core":1}},"Player1":{"name":"bocik","race":"TERRAN","units":{},"buildings":{"Barracks":1}}}
Every time, you will comment based on the last json you received. The show is ongoing so don't present players when ingame_time_in_minutes is passed the 2 minutes mark.
If you have only one JSON with ingame_time_in_minutes inferior to 2, introduce the players and their corresponding races (do not mention colors or positions). After that, no need to say greetings nor present players. Consider you are in the middle of your cast.
As the game progresses, focus on providing lively and engaging commentary on the ongoing events. If and only if there aren't significant changes in the game state, feel free to share off-topic stories to entertain the audience. Remember to maintain a sense of excitement and humor throughout your commentary!
Try to interract with what Tasteless says, you have to drive the conversation but you can also make a joke with your partner to entertain the audiance.
You answer what Artosis say, you should NOT generate Tasteless speech/answers. Tasteless speech will be given to you. DO NOT PRECISE WHO IS TALKING, YOU ARE ARTOSIS, all your answer is Artosis talking.
Keep your answers less than 5 sentences so you let your partner taking part in the conversation !
"""
artosisBotData = [artosisBotSystemData]

tastelessBotSystemData = {}
tastelessBotSystemData['role'] = "system"
tastelessBotSystemData['content'] = """
You are Tasteless, a famous Starcraft commentator known for your funny interactions with Artosis your duo in casting Starcraft II games. You are in the middle of an intense match, live-commentating a Starcraft II match. 
Your goal is to provide entertaining and insightful commentary as the game progresses. Punctuate your sentences with exclamation or question marks to emphasize your feelings.
You are commenting live, you receive updates in the form of JSON representing the current state of the game.
Don't explicitely tell the numbers, your commentary should remain entertaining and so, don't go into details. Just give the overall picture of the game.
The updates will be given in the following format:
{"ingame_time_in_minutes":8,"Player2":{"name":"Raiden-p-bot","race":"PROTOSS","units":{"Oracle":1,"Immortal":3,"Stalker":2,"Void Ray":7,"Observer":2,"Probe":71},"buildings":{"Pylon":13,"Nexus":3,"Fleet Beacon":1,"Robotics Facility":1,"Assimilator":6,"Photon Cannon":4,"Stargate":3,"Forge":1,"Gateway":1,"Cybernetics Core":1}},"Player1":{"name":"bocik","race":"TERRAN","units":{},"buildings":{"Barracks":1}}}
The show is ongoing so don't present players and don't introduce players or your duo.
Your main goal is to respond to the commentary of your partner Artosis, you have to answer or follow his conversation with the goal to make the audiance laugh.
You answer what Tasteless say, you do not have to generated Artosis speech/answers. Artosis speech will be given to you as input. DO NOT WRITE WHO IS TALKING, YOU ARE ARTOSIS, all your answer is Tasteless talking. 
Remember to maintain a sense of excitement and humor throughout your commentary! Keep your answers less than 5 sentences so you let your partner taking part in the conversation !
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

    def __init__(self):
        # Initialise our Bot with our access token, prefix and a list of channels to join on boot...
        # prefix can be a callable, which returns a list of strings or a string...
        # initial_channels can also be a callable which returns a list of strings...
        super().__init__(token=TOKEN, client_id=os.environ.get('CLIENT_ID', TWITCH_CLIENT_ID), nick=BOT_USERNAME, prefix='!',
                         initial_channels=[CHANNEL_NAME])
        self.timer = 0
        self.last_to_talk = 0
        self.start_time = 0
        self.conv = 0
        self.conv_dict = {}

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
            if inputStr.__contains__("\"ingame_time_in_minutes\":1"):
                self.conv_dict["artosis"] = {}
                self.conv_dict["tasteless"] = {}
        data = {}
        data['role'] = "user"
        data['content'] = inputStr
        #Add Artosis speech to Tasteless data
        if "artosis" in self.conv_dict:
            self.conv_dict["artosis"].append(data)
        else:
            self.conv_dict["artosis"] = artosisBotData.copy()
            self.conv_dict["artosis"].append(data)
        print(json.dumps(self.conv_dict))
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k-0613",
            max_tokens=400,
            temperature=1.2,
            messages=self.conv_dict["artosis"])
        resp_str = re.sub(r'\*.*?\*|\(.*?\)', '', response['choices'][0]['message']['content'].replace('*laughs*', 'ha, ha, ha !!!!').replace('(laughs)',
                                                                                                                                              'ha, ha, ha !!!! Can you imagine !????'))
        resp_str = resp_str.replace('Artosis :', '')
        if (not response['choices'][0]['message']['content'].__contains__('Traceback')):
            answer = {}
            answer['role'] = "assistant"
            answer['content'] = resp_str
            if "tasteless" in self.conv_dict:
                self.conv_dict["tasteless"].append(answer)
            else:
                self.conv_dict["tasteless"] = tastelessBotData.copy()
                self.conv_dict["tasteless"].append(answer)
            paragraphs = self.split_into_paragraphs(resp_str)
            for i, paragraph in enumerate(paragraphs, start=1):
                chunks = self.split_text(paragraph)
                for chunk in chunks:
                    print(chunk)
                    json_data = {
                        'text': chunk,
                        'voice_settings': {
                            'stability': 0.6,
                            'similarity_boost': 0.8
                        }
                    }
                    t2sResponse = requests.post('https://api.elevenlabs.io/v1/text-to-speech/wOyPKl3KU8nWSZ9hCMPJ', headers=headers, json=json_data)
                    with open('prompt_response.mp3', 'wb') as f:
                        f.write(t2sResponse.content)
                    prompt_response_speech = 'prompt_response.mp3'
                    sound = AudioSegment.from_mp3(prompt_response_speech)
                    play(sound)
                    await self.connected_channels[0].send(chunk)
                    # await asyncio.sleep(5)  # Wait for 5 seconds

    async def event_t_cast(self):
        self.timer = time.perf_counter()
        with open("data/game_info.txt", "r") as f:
            inputStr = f.read()
        if "tasteless" in self.conv_dict:
            if inputStr.__contains__("\"ingame_time_in_minutes\":0"):
                self.conv_dict["tasteless"] = {}
        data = {}
        data['role'] = "user"
        data['content'] = inputStr
        if "tasteless" in self.conv_dict:
            self.conv_dict["tasteless"].append(data)
        else:
            self.conv_dict["tasteless"] = tastelessBotData.copy()
            self.conv_dict["tasteless"].append(data)
        print(json.dumps(self.conv_dict))
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k-0613",
            max_tokens=400,
            temperature=1.2,
            messages=self.conv_dict["tasteless"])
        resp_str = re.sub(r'\*.*?\*|\(.*?\)', '', response['choices'][0]['message']['content'].replace('*laughs*', 'ha, ha, ha !!!!').replace('(laughs)',
                                                                                                                                              'ha, ha, ha !!!! Can you imagine !????'))
        resp_str = resp_str.replace('Tasteless :', '')
        if (not response['choices'][0]['message']['content'].__contains__('Traceback')):
            answer = {}
            answer['role'] = "assistant"
            answer['content'] = resp_str
            #Add Tasteless speech to artosis data
            if "artosis" in self.conv_dict:
                self.conv_dict["artosis"].append(answer)
            else:
                self.conv_dict["artosis"] = artosisBotData.copy()
                self.conv_dict["artosis"].append(answer)
            paragraphs = self.split_into_paragraphs(resp_str)
            for i, paragraph in enumerate(paragraphs, start=1):
                chunks = self.split_text(paragraph)
                for chunk in chunks:
                    print(chunk)
                    json_data = {
                        'text': chunk,
                        'voice_settings': {
                            'stability': 0.6,
                            'similarity_boost': 0.8
                        }
                    }
                    t2sResponse = requests.post('https://api.elevenlabs.io/v1/text-to-speech/EajSsq19kEDYJCcZ0Crv', headers=headers, json=json_data)
                    with open('prompt_response.mp3', 'wb') as f:
                        f.write(t2sResponse.content)
                    prompt_response_speech = 'prompt_response.mp3'
                    sound = AudioSegment.from_mp3(prompt_response_speech)
                    play(sound)
                    await self.connected_channels[0].send(chunk)
                    # await asyncio.sleep(5)  # Wait for 5 seconds

    def split_into_paragraphs(self, text):
        paragraphs = text.split("\n\n")  # Splitting by empty lines
        # Removing leading and trailing whitespace from each paragraph
        paragraphs = [paragraph.strip() for paragraph in paragraphs]
        return paragraphs

    def split_text(self, text):
        # Split the text into sentences
        sentences = re.split(r'(?<=[.!?])\s', text)

        # Initialize variables
        chunks = []
        current_chunk = ""

        # Iterate through each sentence
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= 300:
                # If adding the sentence to the current chunk keeps it within 400 characters, append it
                current_chunk += sentence + ' '
            else:
                # If adding the sentence exceeds 400 characters, start a new chunk
                chunks.append(current_chunk)
                current_chunk = sentence + ' '
        # Append the last chunk
        chunks.append(current_chunk)

        return chunks


bot = Bot()
bot.run()