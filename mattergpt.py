#!/usr/bin/env python3

# MatterGPT 1.0beta1 (2023-03-31)
# Entirely written by ChatGPT (ChatGPT-4 based)
# @2023 AtamaokaC
# Python Party of Osaka University Medical School, Japan
# License: GNU General Public License v3

import os
import sys
import argparse
import logging
import io
import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from mattermostdriver import Driver
import openai as OpenAI

# Initialize Flask app
app = Flask(__name__)
load_dotenv()

# Load environment variables
MATTERMOST_OUTGOING_WEBHOOK_TOKEN = os.environ['MATTERMOST_OUTGOING_WEBHOOK_TOKEN']
MATTERMOST_BOT_TOKEN = os.environ['MATTERMOST_BOT_TOKEN']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']

# Set up OpenAI API
OpenAI.api_key = OPENAI_API_KEY

def get_thread_history(post_id, max_thread_posts, mattermost_url, mattermost_port, mattermost_scheme):
    """Fetch the message history of a thread in Mattermost."""

    url = f"{mattermost_scheme}://{mattermost_url}:{mattermost_port}/api/v4/posts/{post_id}/thread"
    headers = {"Authorization": f"Bearer {MATTERMOST_BOT_TOKEN}"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Failed to get thread history: {response.status_code} - {response.text}")

    thread_data = response.json()

    thread_history = []
    posts = sorted(thread_data["posts"].values(), key=lambda x: x['create_at'])
    for post in posts[-max_thread_posts:]:
        thread_history.append((post["user_id"], post["message"]))

    return thread_history

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhook events from Mattermost."""

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

    # Get thread history
    thread_history = get_thread_history(post_id, args.max_thread_posts, args.mm_url, args.mm_port, args.mm_scheme)

    # Get the post information
    post_info = mm_driver.posts.get_post(post_id)

    # Find the root_id of the thread
    root_id = post_info["root_id"] if post_info["root_id"] else post_id

    # Build the messages list for the API call
    messages = [
        {"role": "system", "content": "You are ChatGPT, a large language model trained by OpenAI."},
    ]

    for (user, msg) in thread_history:
        role = "user" if user != mm_bot_id else "assistant"
        messages.append({"role": role, "content": msg})

    # Generate a response using OpenAI API
    response = OpenAI.ChatCompletion.create(
        model=args.gpt_model,
        messages=messages,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )

    # Extract the generated message
    generated_message = response.choices[0].message['content']

    # Post the generated message as a reply in the thread
    mm_driver.posts.create_post({
        'channel_id': channel_id,
        'message': generated_message,
        'root_id': root_id,
    })

    return jsonify({}), 200

def create_logging_stream(logfile, flush_logs):
    if logfile:
        log_stream = open(logfile, 'a', encoding='utf-8', buffering=1 if flush_logs else -1)
    else:
        log_stream = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=flush_logs)
    
    return log_stream

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mm-url', default=os.environ.get('MATTERGPT_MM_URL', 'localhost'), help='Mattermost server URL')
    parser.add_argument('--mm-port', type=int, default=os.environ.get('MATTERGPT_MM_PORT', 443), help='Mattermost server port')
    parser.add_argument('--mm-scheme', default=os.environ.get('MATTERGPT_MM_SCHEME', 'https'), help='Mattermost server scheme (http or https)')
    parser.add_argument('--webhook-port', type=int, default=os.environ.get('MATTERGPT_WEBHOOK_PORT', 5000), help='Webhook listening port')
    parser.add_argument('--gpt-model', default=os.environ.get('MATTERGPT_GPT_MODEL', 'gpt-3.5-turbo'), help='OpenAI ChatGPT model')
    parser.add_argument('--logfile', default=os.environ.get('MATTERGPT_LOGFILE'), help='Path to log file (default: stdout)')
    parser.add_argument('--loglevel', default=os.environ.get('MATTERGPT_LOGLEVEL', 'INFO'), help='Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
    parser.add_argument('--max-tokens', type=int, default=os.environ.get('MATTERGPT_MAX_TOKENS', 1000), help='Maximum tokens for the generated text')
    parser.add_argument('--temperature', type=float, default=os.environ.get('MATTERGPT_TEMPERATURE', 0.5), help='Temperature for the generated text (higher values make the output more diverse, lower values make it more conservative)')
    parser.add_argument('--max-thread-posts', type=int, default=os.environ.get('MATTERGPT_MAX_THREAD_POSTS', 20), help='Maximum number of posts to fetch in a thread')
    parser.add_argument('--debug', action='store_true', default=os.environ.get('MATTERGPT_DEBUG', False), help='Enable debug mode for Flask')
    parser.add_argument('--flush-logs', action='store_true', default=os.environ.get('MATTERGPT_FLUSH_LOGS', False), help='Enable immediate flushing of logs')
    parser.add_argument('--production', action='store_true', default=os.environ.get('MATTERGPT_PRODUCTION', False), help='Use Gunicorn for production environment')
    return parser.parse_args()

def configure_logging(args):
    loglevel = getattr(logging, args.loglevel.upper(), logging.INFO)
    log_stream = create_logging_stream(args.logfile, args.flush_logs)
    logging.basicConfig(
        stream=log_stream,
        level=loglevel,
        format="[%(asctime)s] %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

app = Flask(__name__)

if __name__ == '__main__':
    args = parse_args()
    configure_logging(args)
    # Set up Mattermost driver
    mm_driver = Driver({
        'url': args.mm_url,
        'port': args.mm_port,
        'scheme': args.mm_scheme,
        'token': MATTERMOST_BOT_TOKEN,
    })

    mm_driver.login()

    # Get bot user ID
    mm_bot_id = mm_driver.users.get_user('me')['id']

    # Run the Flask app
    if args.production:
        os.system(f"gunicorn --bind 0.0.0.0:{args.webhook_port} mattergpt:app")
    else:
        app.run(host='0.0.0.0', port=args.webhook_port, debug=args.debug)
