#!/usr/bin/env python3

# MatterGPT (mattergpt.py) version 1.0.0
# Entirely written by ChatGPT (ChatGPT-4 based)
# @2023 AtamaokaC
# Python Party of Osaka University Medical School, Japan
# License: GNU General Public License v3

import re
import os
import sys
import subprocess
import argparse
import logging
import io
import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify, g
from mattermostdriver import Driver
import openai as OpenAI
from openai.error import OpenAIError


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mm-url', default=os.environ.get('MATTERGPT_MM_URL', 'localhost'), help='Mattermost server URL')
    parser.add_argument('--mm-port', type=int, default=os.environ.get('MATTERGPT_MM_PORT', 443), help='Mattermost server port')
    parser.add_argument('--mm-scheme', default=os.environ.get('MATTERGPT_MM_SCHEME', 'https'), help='Mattermost server scheme (http or https)')
    parser.add_argument('--webhook-host', default=os.environ.get('MATTERGPT_WEBHOOK_HOST', '0.0.0.0'), help='Webhook listening host (default: %(default)s)')
    parser.add_argument('--webhook-port', type=int, default=os.environ.get('MATTERGPT_WEBHOOK_PORT', 5000), help='Webhook listening port')
    parser.add_argument('--gpt-model', default=os.environ.get('MATTERGPT_GPT_MODEL', 'gpt-3.5-turbo'), help='OpenAI ChatGPT model')
    parser.add_argument(
        '--system-message',
        type=str,
        default=os.environ.get('MATTERGPT_SYSTEM_MESSAGE', 'You are ChatGPT, a large language model trained by OpenAI.'),
        help='The system message to include at the beginning of the conversation (default: %(default)s)',
    )
    parser.add_argument(
        '--additional-message',
        type=str,
        default=os.environ.get('MATTERGPT_ADDITIONAL_MESSAGE', ''),
        help='An additional message to include at the beginning of the conversation (default: %(default)s)',
    )
    parser.add_argument('--logfile', default=os.environ.get('MATTERGPT_LOGFILE', None), help='Path to log file (default: stdout)')
    parser.add_argument('--loglevel', default=os.environ.get('MATTERGPT_LOGLEVEL', 'INFO'), help='Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
    parser.add_argument('--max-tokens', type=int, default=os.environ.get('MATTERGPT_MAX_TOKENS', 1000), help='Maximum tokens for the generated text')
    parser.add_argument('--temperature', type=float, default=os.environ.get('MATTERGPT_TEMPERATURE', 0.5), help='Temperature for the generated text (higher values make the output more diverse, lower values make it more conservative)')
    parser.add_argument('--top-p', type=float, default=os.environ.get('MATTERGPT_TOP_P', 1.0), help='The value of top_p for the generated text (float between 0 and 1)')
    parser.add_argument('--frequency-penalty', type=float, default=os.environ.get('MATTERGPT_FREQUENCY_PENALTY', 0.0), help='The value of frequency_penalty for the generated text (float between -2 and 2)')
    parser.add_argument('--presence-penalty', type=float, default=os.environ.get('MATTERGPT_PRESENCE_PENALTY', 0.0), help='The value of presence_penalty for the generated text (float between -2 and 2)')
    parser.add_argument('--max-thread-posts', type=int, default=os.environ.get('MATTERGPT_MAX_THREAD_POSTS', 0), help='Maximum number of posts to fetch in a thread (0 means unlimited)')
    parser.add_argument('--max-thread-tokens', type=int, default=os.environ.get('MATTERGPT_MAX_THREAD_TOKENS', 4096), help='Maximum tokens to include from the thread history')
    parser.add_argument('--debug', action='store_true', default=str(os.environ.get('MATTERGPT_DEBUG', 'false')).lower() == 'true', help='Enable debug mode')
    parser.add_argument('--flush-logs', action='store_true', default=os.environ.get('MATTERGPT_FLUSH_LOGS', 'false').lower() == 'true', help='Enable immediate flushing of logs')
    parser.add_argument('--gunicorn-path', default=os.environ.get('MATTERGPT_GUNICORN_PATH'), help='Path to Gunicorn executable (if not provided, Flask built-in server will be used)')
    parser.add_argument('--workers', type=int, default=os.environ.get('MATTERGPT_WORKERS', 1), help='Number of Gunicorn worker processes (only applicable if using Gunicorn)')
    parser.add_argument('--timeout', type=int, default=os.environ.get('MATTERGPT_TIMEOUT', 30), help='Gunicorn timeout value in seconds (only applicable if using Gunicorn)')
    args = parser.parse_args()

    os.environ['MATTERGPT_MM_URL'] = args.mm_url
    os.environ['MATTERGPT_MM_PORT'] = str(args.mm_port)
    os.environ['MATTERGPT_MM_SCHEME'] = args.mm_scheme
    os.environ['MATTERGPT_WEBHOOK_HOST'] = args.webhook_host
    os.environ['MATTERGPT_WEBHOOK_PORT'] = str(args.webhook_port)
    os.environ['MATTERGPT_GPT_MODEL'] = args.gpt_model
    os.environ["MATTERGPT_SYSTEM_MESSAGE"] = args.system_message
    os.environ['MATTERGPT_ADDITIONAL_MESSAGE'] = args.additional_message
    os.environ['MATTERGPT_LOGFILE'] = args.logfile if args.logfile else ''
    os.environ['MATTERGPT_LOGLEVEL'] = args.loglevel
    os.environ['MATTERGPT_MAX_TOKENS'] = str(args.max_tokens)
    os.environ['MATTERGPT_TEMPERATURE'] = str(args.temperature)
    os.environ['MATTERGPT_TOP_P'] = str(args.top_p)
    os.environ['MATTERGPT_FREQUENCY_PENALTY'] = str(args.frequency_penalty)
    os.environ['MATTERGPT_PRESENCE_PENALTY'] = str(args.presence_penalty)
    os.environ['MATTERGPT_MAX_THREAD_POSTS'] = str(args.max_thread_posts)
    os.environ['MATTERGPT_MAX_THREAD_TOKENS'] = str(args.max_thread_tokens)
    os.environ['MATTERGPT_DEBUG'] = str(int(args.debug))
    os.environ['MATTERGPT_FLUSH_LOGS'] = str(int(args.flush_logs))
    os.environ['MATTERGPT_GUNICORN_PATH'] = args.gunicorn_path if args.gunicorn_path else ''
    os.environ['MATTERGPT_WORKERS'] = str(args.workers)
    os.environ['MATTERGPT_TIMEOUT'] = str(args.timeout)

    return args

def setup_logger(name, log_level=logging.DEBUG, log_file=None):
    # Set up the logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Configure log output to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter('[%(asctime)s] %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Configure log output to a file (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter('[%(asctime)s] %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger

def create_logging_stream(logfile, flush_logs):
    if logfile:
        log_stream = open(logfile, 'a', encoding='utf-8', buffering=1 if flush_logs else -1)
    else:
        log_stream = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=flush_logs)
    
    return log_stream

def configure_logging(args):
    loglevel = getattr(logging, args.loglevel.upper(), logging.INFO)
    log_stream = create_logging_stream(args.logfile, args.flush_logs)
    logging.basicConfig(
        stream=log_stream,
        level=loglevel,
        format="[%(asctime)s] %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def tokenize(text):
    """
    Tokenize the given text using a simple method.
    This is a simple approximation and may not be accurate for all languages.
    """
    # Regular expression to match words in English and other languages
    word_pattern = re.compile(r'\w+|\S')

    # Use the regular expression to find words in the text
    words = word_pattern.findall(text)

    return words

def estimate_token_count(text):
    """
    Estimate the number of tokens in the given text.
    This is a simple approximation and may not be accurate for all languages.
    """
    tokens = tokenize(text)

    # Return the number of words found
    return len(tokens)

def get_thread_history(post_id, max_thread_posts, max_thread_tokens, mattermost_url, mattermost_port, mattermost_scheme):
    """Fetch the message history of a thread in Mattermost."""

    url = f"{mattermost_scheme}://{mattermost_url}:{mattermost_port}/api/v4/posts/{post_id}/thread"
    headers = {"Authorization": f"Bearer {MATTERMOST_BOT_TOKEN}"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Failed to get thread history: {response.status_code} - {response.text}")

    thread_data = response.json()

    thread_history = []
    posts = sorted(thread_data["posts"].values(), key=lambda x: x['create_at'])
    accumulated_tokens = 0
    for post in reversed(posts):
        tokenized = tokenize(post["message"])
        message_tokens = len(tokenize(post["message"]))
        logging.debug(f"Tokenized message: {tokenized}")
        logging.debug(f"Message tokens: {message_tokens}")
        if accumulated_tokens + message_tokens <= max_thread_tokens:
            thread_history.append((post["user_id"], post["message"]))
            accumulated_tokens += message_tokens
        else:
            break

    thread_history.reverse()

    return thread_history

def init_mattermost_driver(args):
    mm_driver = Driver({
        'url': args.mm_url,
        'port': args.mm_port,
        'scheme': args.mm_scheme,
        'token': MATTERMOST_BOT_TOKEN,
    })
    mm_driver.login()
    return mm_driver

def create_app(args):
    app = Flask(__name__)

    @app.before_request
    def store_args():
        g.args = args

    @app.route('/webhook', methods=['POST'])
    def webhook():
        """Handle incoming webhook events from Mattermost."""
        logging.debug(f"Webhook received: {request.json}")

        args = g.args
        data = request.json
        token = data.get('token')

        # Verify the webhook token
        if token != MATTERMOST_OUTGOING_WEBHOOK_TOKEN:
            return jsonify({'text': 'Invalid token'}), 403

        user_id = data.get('user_id')

        # Ignore messages from the bot itself
        if user_id == mm_bot_id:
            return jsonify({}), 200

        post_id = data.get('post_id')
        channel_id = data.get('channel_id')

        # Get the post information
        post_info = mm_driver.posts.get_post(post_id)

        # Find the root_id of the thread
        root_id = post_info["root_id"] if post_info["root_id"] else post_id

        # Calculate tokens for additional_message
        additional_message_tokens = estimate_token_count(args.additional_message)

        # Get thread history
        thread_history = get_thread_history(root_id, args.max_thread_posts, args.max_thread_tokens - args.max_tokens - additional_message_tokens, args.mm_url, args.mm_port, args.mm_scheme)

        # Calculate the estimated tokens for the current thread
        estimated_thread_tokens = sum(estimate_token_count(msg) for _, msg in thread_history)

        # Add the additional_message tokens
        estimated_thread_tokens += additional_message_tokens

        # Set buffer tokens to be equal to max_tokens
        buffer_tokens = args.max_tokens

        # Reduce thread_history if necessary
        while estimated_thread_tokens + buffer_tokens > args.max_thread_tokens and len(thread_history) > 0:
            removed_user, removed_message = thread_history.pop(0)
            estimated_thread_tokens -= estimate_token_count(removed_message)

        # Build the messages list for the API call
        messages = [
            {"role": "system", "content": args.system_message},
        ]

        for (user, msg) in thread_history:
            role = "user" if user != mm_bot_id else "assistant"
            messages.append({"role": role, "content": msg})

        # Add additional_message
        messages[-1]['content'] += f'\n{args.additional_message}'

        # Generate a response using OpenAI API
        retry = True
        while retry:
            try:
                logging.debug(f"Messages sent: {messages}")
                # Generate a response using OpenAI API
                response = OpenAI.ChatCompletion.create(
                    model=args.gpt_model,
                    messages=messages,
                    max_tokens=args.max_tokens,
                    temperature=args.temperature,
                    top_p=args.top_p,
                    frequency_penalty=args.frequency_penalty,
                    presence_penalty=args.presence_penalty,
                )
                retry = False
            except OpenAIError as e:
                if e.error.get('code') == 'context_length_exceeded':
                    logging.info(f"Context length exceeded. Retry...")
                    # Remove the oldest message and try again
                    messages.pop(1)
                else:
                    raise e

        # Extract the generated message
        generated_message = response.choices[0].message['content']

        # Post the generated message as a reply in the thread
        mm_driver.posts.create_post({
            'channel_id': channel_id,
            'message': generated_message,
            'root_id': root_id,
        })

        return jsonify({}), 200

    return app


if __name__ == "__main__":
    load_dotenv()
else:
    sys.argv = ['mattergpt']

# Load environment variables
MATTERMOST_OUTGOING_WEBHOOK_TOKEN = os.environ['MATTERMOST_OUTGOING_WEBHOOK_TOKEN']
MATTERMOST_BOT_TOKEN = os.environ['MATTERMOST_BOT_TOKEN']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']

# Set up OpenAI API
OpenAI.api_key = OPENAI_API_KEY

args = parse_args()
configure_logging(args)
mm_driver = init_mattermost_driver(args)
mm_bot_id = mm_driver.users.get_user('me')['id']

if __name__ == "__main__":
    if args.gunicorn_path:
        subprocess.run([args.gunicorn_path, "--workers", str(args.workers), "--timeout", str(args.timeout), "--bind", f"{args.webhook_host}:{args.webhook_port}", "mattergpt:app"])
    else:
        app = create_app(args)
        app.run(host=args.webhook_host, port=args.webhook_port, debug=args.debug)
elif __name__ == "mattergpt":
    app = create_app(args)
