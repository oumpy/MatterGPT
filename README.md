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

You can use command-line options to change the following settings:

- `--mm-url`: Mattermost server URL (default: 'localhost')
- `--mm-port`: Mattermost server port (default: 443)
- `--mm-scheme`: Mattermost server scheme (default: 'https')
- `--webhook-host`: Webhook listening host (default: '0.0.0.0')
- `--webhook-port`: Webhook listening port (default: 5000)
- `--gpt-model`: OpenAI ChatGPT model (default: 'gpt-3.5-turbo')
- `--system-message`: The system message to include at the beginning of the conversation (default: 'You are ChatGPT, a large language model trained by OpenAI.')
- `--additional-message`: An additional message to include at the beginning of the conversation (default: '')
- `--logfile`: Path to log file (default: stdout)
- `--loglevel`: Logging level (default: 'INFO')
- `--max-tokens`: Maximum tokens for the generated text (default: 1000)
- `--temperature`: Temperature for the generated text (default: 0.5)
- `--top-p`: The value of top_p for the generated text (default: 1.0)
- `--frequency-penalty`: The value of frequency_penalty for the generated text (default: 0.0)
- `--presence-penalty`: The value of presence_penalty for the generated text (default: 0.0)
- `--max-thread-posts`: Maximum number of posts to fetch in a thread (0 means unlimited) (default: 0)
- `--max-thread-tokens`: Maximum tokens to include from the thread history (default: 4096)
- `--debug`: Enable debug mode
- `--flush-logs`: Enable immediate flushing of logs
- `--gunicorn-path`: Path to the Gunicorn executable (if not provided, Flask built-in server will be used)
- `--workers`: Number of Gunicorn worker processes (only applicable if using Gunicorn; default: 1)
- `--timeout`: Gunicorn timeout value in seconds (only applicable if using Gunicorn; default: 30)

For more information, run `python mattergpt.py --help`.

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

- @2023 AtamaokaC  
  Python Party of Osaka University Medical School, Japan
- License: GNU General Public License v3

## Disclaimer

This project uses the ChatGPT API provided by OpenAI and assumes no responsibility for the use or results of the API.
Compatibility with Mattermost is also not guaranteed. Use of this project is at your own risk.
