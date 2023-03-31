# MatterGPT

MatterGPT is a ChatGPT-based chatbot that works with Mattermost, engaging users in natural conversations, answering questions, and providing information.

## Version Information

- MatterGPT 1.0beta1
- Development Year: 2023
- Copyright Holder: AtamaokaC
- Affiliation: Python Party of Osaka University Medical School, Japan
- License: GNU General Public License v3

## Prerequisites

1. Install [Python](https://www.python.org/downloads/) (version 3.6 or higher).
2. Clone or download this repository.
3. Run `pip install -r requirements.txt` to install the required packages.

## Usage

1. Create a `.env` file and set the following environment variables:

```
MATTERMOST_OUTGOING_WEBHOOK_TOKEN=your_mattermost_outgoing_webhook_token
MATTERMOST_BOT_TOKEN=your_mattermost_bot_token
OPENAI_API_KEY=your_openai_api_key
```


2. Run the following command in the command line to start the webhook server:

```
$ python main.py
```


3. Set up an Outgoing Webhook in Mattermost and specify the server URL (e.g., http://your_server_ip:5000/webhook).

## Options

You can use command-line options to change the following settings:

- Mattermost server URL, port, and scheme
- Webhook server port
- OpenAI model to use
- Log file path
- Log level
- Maximum tokens for the generated text
- Temperature for the generated text (controls output diversity)
- Maximum number of posts to fetch in a thread

For more information, run `python main.py --help`.

## Disclaimer

This project uses the ChatGPT API provided by OpenAI and assumes no responsibility for the use or results of the API. Compatibility with Mattermost is also not guaranteed. Use of this project is at your own risk.
