# MatterGPT

MatterGPT is a ChatGPT-based chatbot that works with Mattermost, engaging users in natural conversations, answering questions, and providing information.
The codes of this project are developped entirely by ChatGPT.

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
$ python mattergpt.py
```

3. Set up an Outgoing Webhook in Mattermost and specify the server URL (e.g., http://your_server_ip:5000/webhook).

## Options

You can use command-line options to change the following settings:

- `--mm-url`: Mattermost server URL (default: 'localhost')
- `--mm-port`: Mattermost server port (default: 443)
- `--mm-scheme`: Mattermost server scheme (default: 'https')
- `--webhook-port`: Webhook listening port (default: 5000)
- `--gpt-model`: OpenAI ChatGPT model (default: 'gpt-3.5-turbo')
- `--logfile`: Path to log file (default: stdout)
- `--loglevel`: Logging level (default: 'INFO')
- `--max-tokens`: Maximum tokens for the generated text (default: 100)
- `--temperature`: Temperature for the generated text (default: 0.5)
- `--max-thread-posts`: Maximum number of posts to fetch in a thread (default: 20)

For more information, run `python mattergpt.py --help`.

## systemd Unit File Template

A systemd unit file template named `mattergpt.service` is provided in the repository. Adjust the paths and other configurations as needed.

## Copyright & License

- @2023 AtamaokaC  
  Python Party of Osaka University Medical School, Japan
- License: GNU General Public License v3

## Disclaimer

This project uses the ChatGPT API provided by OpenAI and assumes no responsibility for the use or results of the API. Compatibility with Mattermost is also not guaranteed. Use of this project is at your own risk.
