# MatterGPT

MatterGPT is a ChatGPT-based chatbot that works with Mattermost, engaging users in natural conversations, answering questions, and providing information.
The code (and also this README) for this project was developed entirely by ChatGPT.

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

For development and testing:
```
$ python mattergpt.py
```

For production:
```
$ export FLASK_APP=mattergpt.py
$ export MATTERGPT_ENV=production
$ export MATTERGPT_MM_URL=your_mattermost_url
$ export MATTERGPT_MM_PORT=your_mattermost_port
$ export MATTERGPT_MM_SCHEME=your_mattermost_scheme
$ export MATTERGPT_WEBHOOK_PORT=your_webhook_port
$ export MATTERGPT_GPT_MODEL=your_gpt_model
$ export MATTERGPT_LOGFILE=your_logfile_path
$ export MATTERGPT_LOGLEVEL=your_loglevel
$ export MATTERGPT_MAX_TOKENS=your_max_tokens
$ export MATTERGPT_TEMPERATURE=your_temperature
$ export MATTERGPT_MAX_THREAD_POSTS=your_max_thread_posts
$ export MATTERGPT_FLUSH_LOGS=your_flush_logs
$ gunicorn -w 4 -b 0.0.0.0 mattergpt:app
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
- `--flush-logs`: Enable immediate flushing of logs. Note that enabling this option might reduce performance.
- `--production`: Enable production mode (default: False). Use this option when running the script with Gunicorn for better performance and stability in production environments.

For more information, run `python mattergpt.py --help`.

## systemd Unit File Template

A systemd unit file template named `mattergpt.service` is provided in the repository.
Adjust the paths and other configurations as needed.

## Copyright & License

- @2023 AtamaokaC  
  Python Party of Osaka University Medical School, Japan
- License: GNU General Public License v3

## Disclaimer

This project uses the ChatGPT API provided by OpenAI and assumes no responsibility for the use or results of the API.
Compatibility with Mattermost is also not guaranteed. Use of this project is at your own risk.
