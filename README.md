# Starcraft II Live Commentary Bot

This project implements a live commentary system for Starcraft II matches using AI-generated speech and OpenAI's text-to-speech (TTS) technology. The system features two AI commentators, Echo and Vixen, who provide entertaining and insightful commentary based on the current game state.

real casters' voice cloning : 
[![Video Title](https://img.youtube.com/vi/krkvMkw7RdE/0.jpg)](https://www.youtube.com/watch?v=krkvMkw7RdE)

gpt-4 with openai TTS:
[![Video Title](https://img.youtube.com/vi/e4bQoqO6J7c/0.jpg)](https://www.youtube.com/watch?v=e4bQoqO6J7c)

## Features

1. **Dual AI Commentators**: Two distinct AI personalities (Echo and Vixen) provide alternating commentary, creating a dynamic and engaging experience.

2. **Real-time Game State Processing**: The system reads game information from a file (`data/game_info.txt`) and uses it to generate contextually relevant commentary.

3. **OpenAI GPT-4 Integration**: Utilizes the GPT-4 model to generate human-like commentary based on the game state and previous interactions.

4. **Text-to-Speech (TTS) Output**: Converts the generated commentary to speech using OpenAI's TTS API, with different voices for each commentator.

5. **Twitch Integration**: Built to work as a Twitch bot, allowing for potential live streaming capabilities.

6. **Configurable**: Uses a `config.ini` file to store API keys and other configuration details.

7. **Adaptive Commentary**: The AI commentators maintain context over time and can reference previous comments or game events.

## Requirements

- Python 3.x
- OpenAI API key
- Twitch API credentials
- MPV media player (for audio playback)

## Setup

1. Install required Python packages:
   ```
   pip install twitchio openai
   ```

2. Ensure MPV is installed and added to your system's PATH.

3. Create a `config.ini` file with the following structure:
   ```
   [API_KEYS]
   channel-name=YOUR_CHANNEL_NAME
   bot-username=YOUR_BOT_USERNAME
   twitch-token=YOUR_TWITCH_TOKEN
   openapi-key=YOUR_OPENAI_API_KEY
   twitch-client-id=YOUR_TWITCH_CLIENT_ID
   ```

4. Prepare a system to update the `data/game_info.txt` file with the current game state in JSON format.

## Usage

Run the script:

```
python commentary_duo_gpt_openai_tts.py
```

The bot will connect to the specified Twitch channel and start generating commentary based on the game state provided in `data/game_info.txt`.

## How It Works

1. The script initializes two AI commentators with distinct personalities and roles.
2. It periodically checks for updates in the game state file.
3. When an update is detected, it generates commentary using the GPT-4 model.
4. The generated text is converted to speech using OpenAI's TTS API.
5. The audio is played using the MPV media player.
6. The commentators alternate, creating a dialogue-like experience.

## Customization

- Modify the system prompts in `artosisBotSystemData` and `tastelessBotSystemData` to adjust the commentators' personalities and knowledge base.
- Adjust the `min_chunk_size` and timing parameters to fine-tune the commentary flow.

## Limitations

- Requires manual updating of the game state file.
- Depends on external services (OpenAI API, Twitch API) and their respective rate limits.
- Audio playback requires MPV to be installed and configured correctly.

## Contributing

Contributions to improve the project are welcome. Please submit pull requests or open issues for any bugs or feature requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
