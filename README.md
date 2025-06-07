# MatterGPT (version 1.1.0)

MatterGPT is a ChatGPT-based chatbot that works with Mattermost, engaging users in natural conversations, answering questions, and providing information.
The code (and also this README) for this project was developed entirely by ChatGPT.

## Prerequisites

1. Install [Python](https://www.python.org/downloads/) (version 3.6 or higher).
2. Clone or download this repository.
3. Run `pip install -r requirements.txt` to install the required packages.

## Usage

1. Create a `.env` file and set the following environment variables:

```
MATTERGPT_OUTGOING_WEBHOOK_TOKEN=your_mattermost_outgoing_webhook_token
MATTERGPT_MM_BOT_TOKEN=your_mattermost_bot_token
MATTERGPT_OPENAI_API_KEY=your_openai_api_key
```

You can also set other `MATTERGPT_...` environment variables in the `.env` file to change the default values of the corresponding command-line options. 
For example, to change the default Mattermost server URL, add the following line to the `.env` file:

```
MATTERGPT_MM_URL=your_mattermost_url
```

2. Run the following command in the command line to start the webhook server:

```
$ python mattergpt.py
```

3. Set up an Outgoing Webhook in Mattermost and specify the server URL (e.g., http://your_server_ip:5000/webhook).

## Options

You can use command-line options / environment variables, to change the following settings:

| Option                 | Environment Variable         | Default                 | Description                                                                                                          |
|------------------------|------------------------------|-------------------------|----------------------------------------------------------------------------------------------------------------------|
| --mm-url               | MATTERGPT_MM_URL             | localhost               | Mattermost server URL                                                                                                |
| --mm-port              | MATTERGPT_MM_PORT            | 443                     | Mattermost server port                                                                                               |
| --mm-scheme            | MATTERGPT_MM_SCHEME          | https                  | Mattermost server scheme (http or https)                                                                             |
| --webhook-host         | MATTERGPT_WEBHOOK_HOST       | 0.0.0.0                 | Webhook listening host                                                                                               |
| --webhook-port         | MATTERGPT_WEBHOOK_PORT       | 5000                    | Webhook listening port                                                                                               |
| --outgoing-webhook-token | MATTERGPT_OUTGOING_WEBHOOK_TOKEN | (blank)           | Mattermost outgoing-webhook Token                                                                                                  |
| --mm-bot-token         | MATTERGPT_MM_BOT_TOKEN       | (blank)                 | Mattermost Bot- Token                                                                                                  |
| --openai-api-key       | MATTERGPT_OPENAI_API_KEY     | (blank)                 | OpenAI API Key                                                                             |
| --gpt-model            | MATTERGPT_GPT_MODEL          | gpt-3.5-turbo           | OpenAI ChatGPT model                                                                                                 |
| --system-message       | MATTERGPT_SYSTEM_MESSAGE     | (Default system message)| The system message to include at the beginning of the conversation                                                   |
| --additional-message   | MATTERGPT_ADDITIONAL_MESSAGE |                         | An additional message to include at the beginning of the conversation                                                 |
| --logfile              | MATTERGPT_LOGFILE            | (stdout)                | Path to log file                                                                                                     |
| --loglevel             | MATTERGPT_LOGLEVEL           | INFO                    | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)                                                                |
| --max-tokens           | MATTERGPT_MAX_TOKENS         | 1000                    | Maximum tokens for the generated text                                                                                |
| --temperature          | MATTERGPT_TEMPERATURE        | 0.5                     | Temperature for the generated text (higher values make the output more diverse, lower values make it more conservative) |
| --top-p                | MATTERGPT_TOP_P              | 1.0                     | The value of top_p for the generated text (float between 0 and 1)                                                     |
| --frequency-penalty    | MATTERGPT_FREQUENCY_PENALTY  | 0.0                     | The value of frequency_penalty for the generated text (float between -2 and 2)                                        |
| --presence-penalty     | MATTERGPT_PRESENCE_PENALTY   | 0.0                     | The value of presence_penalty for the generated text (float between -2 and 2)                                         |
| --max-thread-posts     | MATTERGPT_MAX_THREAD_POSTS   | 0                       | Maximum number of posts to fetch in a thread (0 means unlimited)                                                      |
| --max-thread-tokens    | MATTERGPT_MAX_THREAD_TOKENS  | 4096                    | Maximum tokens to include from the thread history                                                                    |
| --debug                | MATTERGPT_DEBUG              | false                   | Enable debug mode                                                                                                    |
| --flush-logs           | MATTERGPT_FLUSH_LOGS         | false                   | Enable immediate flushing of logs                                                                                    |
| --gunicorn-path        | MATTERGPT_GUNICORN_PATH      | (Not provided)          | Path to Gunicorn executable (if not provided, Flask built-in server will be used)                                    |
| --workers              | MATTERGPT_WORKERS            | 1                       | Number of Gunicorn worker processes (only applicable if using Gunicorn)                                               |
| --timeout              | MATTERGPT_TIMEOUT            | 30                      | Gunicorn timeout value in seconds (only applicable if using Gunicorn)                                                 |

## Custom Commands

MatterGPT now supports custom commands that you can define in a separate Python file. 
Simply create a file named `custom_commands.py` in the same directory as mattergpt.py, and define your custom commands as Python functions. 
The custom command functions should accept a single argument representing the message text and return a string with the response.

Here's an example of how to create a custom command:

```
# custom_commands.py

def hello_world(message):
    return "Hello, world!"
```

To call this custom command from Mattermost, simply mention the bot and use the command as follows:
```
@your_bot_name !hello_world
```

MatterGPT will automatically detect and execute the custom command, returning the response in the chat.

### Custom Command Guidelines

1. Custom command function names should be lowercase and use underscores to separate words (e.g., my_custom_command).
2. Custom commands should be defined in the custom_commands.py file in the same directory as mattergpt.py.
3. Custom command functions should accept a single argument representing the message text and return a string with the response.
4. To call a custom command from Mattermost, mention the bot and use the command prefixed with an exclamation mark (e.g., @your_bot_name !my_custom_command).

## systemd Unit File Template

A systemd unit file template named `mattergpt.service` is provided in the repository.
Adjust the paths and other configurations as needed.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## Copyright & License

- @2023-2025 AtamaokaC  
  Python Party of Osaka University Medical School, Japan
- License: GNU General Public License v3

## Disclaimer

This project uses the ChatGPT API provided by OpenAI and assumes no responsibility for the use or results of the API.
Compatibility with Mattermost is also not guaranteed. Use of this project is at your own risk.
