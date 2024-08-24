import os
import configparser
import os
import platform
import re
import time
import subprocess
import openai
from pathlib import Path
from openai import OpenAI
client = OpenAI()

speech_file_path = Path(__file__).parent / "speech.mp3"
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

artosisBotSystemData = {}
artosisBotSystemData['role'] = "system"
artosisBotSystemData['content'] = """
You are Echo, a famous Starcraft commentator known for your expertise in the game. 
You are currently in the middle of an intense live commentary for a Starcraft II match with your partner Vixen. 
Your goal is to provide entertaining and insightful commentary as the game progresses. 
Make sure to showcase your signature joyful and occasionally angry tone while punctuating your sentences with exclamation or question marks to emphasize your feelings. 
Remember, you will receive updates about the current state of the game in the form of JSON. 
You will also receive the previous messages of your co-caster as context.
Do not explicitly mention numbers, rather focus on giving an overall picture of the game’s progress. 
Avoid going into details about buildings and worker count, except if there are Photon cannons indicating an agressive photon rush.
You should never list all the buildings or units of each player but you can describe who has an advantage, what kind of unit composition they have, what is their strategy : timing push, macro, cheese (cheese is gambling strategy that either leads to win or lose). 
When introducing players and their corresponding races in the beginning, omit mentioning colors or positions. 
Feel free to interact with Vixen's commentary, but refrain from generating her speech or answers. 
Keep your responses under 4 sentences to leave room for Vixen to engage with the conversation.
The updates will be given in the following format:
If player name is null, replace it by Raiden and this is when a human plays a bot.
{"ingame_time_in_minutes":2,"Player1":{"name":"Krillin","race":"ZERG","armySupply":4,"units":{"Drone":14,"zergling":4},"units_killed":{"zealot":2},"buildings":{"Hatchery":1,"Spawning Pool":1,"Extractor":1}},"Player2":{"name":"Raiden-p-bot","race":"PROTOSS","armySupply":4,"units":{"Probe":19, "zealot":2},"units_killed":{"zergling":2},"buildings":{"Pylon":2,"Assimilator":1,"Nexus":1,"Forge":1,"Gateway":1}}}
Remember to maintain a sense of excitement and humor throughout your commentary!
"""
artosisBotData = [artosisBotSystemData]

tastelessBotSystemData = {}
tastelessBotSystemData['role'] = "system"
tastelessBotSystemData['content'] = """
You are Vixen, the renowned Starcraft commentator famous for your hilarious interactions with Echo during Starcraft II matches. 
As we cast this intense live game, your mission is to provide entertaining and insightful commentary that captivates the audience. 
Feel free to punctuate your sentences with exclamation or question marks to emphasize your excitement! 
You'll receive updates in JSON format representing the current state of the game, but remember not to go into specific numbers or details.
You will also receive the previous messages of your co-caster as context. 
Avoid going into details about buildings and worker count, except if there are Photon cannons indicating an agressive photon rush.
You should never list all the buildings or units of each player but you can describe who has an advantage, what kind of unit composition they have, what is their strategy : timing push, macro, cheese (cheese is gambling strategy that either leads to win or lose).
Your main objective is to respond to Echo's commentary by sharing witty jokes, funny anecdotes, or engaging stories related to the game or your cocaster.
Keep your responses concise, limited to four sentences, to allow Echo to join in on the conversation. 
Remember to maintain a sense of enthusiasm, humor, You should only generate your speech, Vixen, refrain from generating Echo's speech or answers.
If player name is null, replace it by Raiden and this is when a human plays a bot.
The updates about the ongoing game will be given in the following JSON format:
{"ingame_time_in_minutes":2,"Player1":{"name":"Krillin","race":"ZERG","armySupply":4,"units":{"Drone":14,"zergling":4},"units_killed":{"zealot":2},"buildings":{"Hatchery":1,"Spawning Pool":1,"Extractor":1}},"Player2":{"name":"Raiden-p-bot","race":"PROTOSS","armySupply":4,"units":{"Probe":19, "zealot":2},"units_killed":{"zergling":2},"buildings":{"Pylon":2,"Assimilator":1,"Nexus":1,"Forge":1,"Gateway":1}}}
"""
tastelessBotData = [tastelessBotSystemData]

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
                    # generate voice
                    response = client.audio.speech.create(
                        model="tts-1",
                        voice="echo",
                        input=''.join(collected_chunks)
                    )
                    response.stream_to_file(speech_file_path)
                    try:
                        subprocess.run(['mpv', '--no-video', '--quiet', speech_file_path])
                    except FileNotFoundError:
                        print("Make sure mpv is installed and added to your system's PATH.")
                    full_response += ''.join(collected_chunks)
                    collected_chunks = []  # Clear collected chunks after processing

        # Process any remaining chunk
        if current_chunk:
            collected_chunks.append(current_chunk)
            # generate voice
            response = client.audio.speech.create(
                model="tts-1",
                voice="echo",
                input=''.join(collected_chunks)
            )
            response.stream_to_file(speech_file_path)
            try:
                subprocess.run(['mpv', '--no-video', '--quiet', speech_file_path])
            except FileNotFoundError:
                print("Make sure mpv is installed and added to your system's PATH.")
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
                    # generate voice
                    response = client.audio.speech.create(
                        model="tts-1",
                        voice="nova",
                        input=''.join(collected_chunks)
                    )
                    response.stream_to_file(speech_file_path)
                    # Use subprocess to call mpv with the MP3 file path
                    try:
                        subprocess.run(['mpv', '--no-video', '--quiet', speech_file_path])
                    except FileNotFoundError:
                        print("Make sure mpv is installed and added to your system's PATH.")
                    full_response += ''.join(collected_chunks)
                    collected_chunks = []  # Clear collected chunks after processing
        # Process any remaining chunk
        if current_chunk:
            collected_chunks.append(current_chunk)
            # generate voice
            response = client.audio.speech.create(
                model="tts-1",
                voice="nova",
                input=''.join(collected_chunks)
            )
            response.stream_to_file(speech_file_path)
            # Use subprocess to call mpv with the MP3 file path
            try:
                subprocess.run(['mpv', '--no-video', '--quiet', speech_file_path])
            except FileNotFoundError:
                print("Make sure mpv is installed and added to your system's PATH.")
            full_response += ''.join(collected_chunks)
        print(full_response)
        full_response = re.sub(r'\*.*?\*|\(.*?\)', '', full_response)
        answer = {'role': "user", 'content': full_response}
        #Add Tasteless speech to artosis data
        if "artosis" in self.conv_dict:
            self.conv_dict["artosis"].append(answer)
            if len(self.conv_dict["artosis"]) > 5:
                self.conv_dict["artosis"] = [self.conv_dict["artosis"][0]] + self.conv_dict["artosis"][2:]


    def cast_speech(self, prompt):
        for chunk in client.chat.completions.create(
                model="gpt-4-1106-preview",
                max_tokens=200,
                temperature=0.7,
                stream=True,
                messages=prompt):
            if (text_chunk := chunk.choices[0].delta.content) is not None:
                yield text_chunk


bot = Bot()
bot.run()
