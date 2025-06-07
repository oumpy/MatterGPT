#!/usr/bin/env python3

# MatterGPT (mattergpt.py) version 1.1.0
# Entirely written by ChatGPT (ChatGPT-4o based)
# @2023-2025 AtamaokaC
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
import openai
from openai import OpenAI, OpenAIError, BadRequestError
from openai import OpenAIError, APIError, RateLimitError, APITimeoutError, InternalServerError, AuthenticationError

# Initialize OpenAI client with API key after loading .env
client = openai.Client(api_key=os.environ['MATTERGPT_OPENAI_API_KEY'])

# ========================
# Argument parsing section
# ========================
def parse_args():
    parser = argparse.ArgumentParser(description="MatterGPT: ChatGPT-powered Mattermost bot")

    # Mattermost and Webhook configuration
    parser.add_argument('--mm-url', default=os.environ.get('MATTERGPT_MM_URL', 'localhost'),
                        help='Mattermost server URL')
    parser.add_argument('--mm-port', type=int, default=os.environ.get('MATTERGPT_MM_PORT', 443),
                        help='Mattermost server port')
    parser.add_argument('--mm-scheme', default=os.environ.get('MATTERGPT_MM_SCHEME', 'https'),
                        help='Mattermost server scheme (http or https)')
    parser.add_argument('--webhook-host', default=os.environ.get('MATTERGPT_WEBHOOK_HOST', '0.0.0.0'),
                        help='Webhook listening host')
    parser.add_argument('--webhook-port', type=int, default=os.environ.get('MATTERGPT_WEBHOOK_PORT', 5000),
                        help='Webhook listening port')

    # Authentication tokens
    parser.add_argument('--outgoing-webhook-token', default=os.environ.get('MATTERGPT_OUTGOING_WEBHOOK_TOKEN'),
                        help='Token for Mattermost outgoing webhook')
    parser.add_argument('--bot-token', default=os.environ.get('MATTERGPT_BOT_TOKEN'),
                        help='Bot token for Mattermost API')
    parser.add_argument('--openai-api-key', default=os.environ.get('MATTERGPT_OPENAI_API_KEY'),
                        help='OpenAI API key')

    # ChatGPT and prompt configuration
    parser.add_argument('--gpt-model', default=os.environ.get('MATTERGPT_GPT_MODEL', 'gpt-3.5-turbo'),
                        help='OpenAI ChatGPT model')
    parser.add_argument('--system-message', default=os.environ.get('MATTERGPT_SYSTEM_MESSAGE',
                                                                    'You are ChatGPT, a large language model trained by OpenAI.'),
                        help='System message at beginning of conversation')
    parser.add_argument('--additional-message', default=os.environ.get('MATTERGPT_ADDITIONAL_MESSAGE', ''),
                        help='Additional user message to be appended')

    # Token and generation control
    parser.add_argument('--max-tokens', type=int, default=int(os.environ.get('MATTERGPT_MAX_TOKENS', 1000)),
                        help='Maximum tokens for the generated text')
    parser.add_argument('--temperature', type=float, default=float(os.environ.get('MATTERGPT_TEMPERATURE', 0.5)),
                        help='Temperature for randomness in output')
    parser.add_argument('--top-p', type=float, default=float(os.environ.get('MATTERGPT_TOP_P', 1.0)),
                        help='Nucleus sampling value')
    parser.add_argument('--frequency-penalty', type=float, default=float(os.environ.get('MATTERGPT_FREQUENCY_PENALTY', 0.0)),
                        help='Frequency penalty for repeated words')
    parser.add_argument('--presence-penalty', type=float, default=float(os.environ.get('MATTERGPT_PRESENCE_PENALTY', 0.0)),
                        help='Penalty for introducing new topics')

    # Thread history controls
    parser.add_argument('--max-thread-posts', type=int, default=int(os.environ.get('MATTERGPT_MAX_THREAD_POSTS', 0)),
                        help='Maximum number of posts to fetch in a thread (0 = unlimited)')
    parser.add_argument('--max-thread-tokens', type=int, default=int(os.environ.get('MATTERGPT_MAX_THREAD_TOKENS', 4096)),
                        help='Maximum tokens allowed from thread history')

    # Logging and server configuration
    parser.add_argument('--logfile', default=os.environ.get('MATTERGPT_LOGFILE'),
                        help='Path to log file (default: stdout)')
    parser.add_argument('--loglevel', default=os.environ.get('MATTERGPT_LOGLEVEL', 'INFO'),
                        help='Logging level')
    parser.add_argument('--debug', action='store_true', default=os.environ.get('MATTERGPT_DEBUG', 'false').lower() == 'true',
                        help='Enable debug mode for Flask')
    parser.add_argument('--flush-logs', action='store_true', default=os.environ.get('MATTERGPT_FLUSH_LOGS', 'false').lower() == 'true',
                        help='Flush logs immediately')

    # Gunicorn
    parser.add_argument('--gunicorn-path', default=os.environ.get('MATTERGPT_GUNICORN_PATH'),
                        help='Path to Gunicorn executable')
    parser.add_argument('--workers', type=int, default=int(os.environ.get('MATTERGPT_WORKERS', 1)),
                        help='Number of Gunicorn worker processes')
    parser.add_argument('--timeout', type=int, default=int(os.environ.get('MATTERGPT_TIMEOUT', 30)),
                        help='Gunicorn timeout in seconds')

    return parser.parse_args()

# ================
# Logging utilities
# ================
def configure_logging(args):
    loglevel = getattr(logging, args.loglevel.upper(), logging.INFO)
    stream = open(args.logfile, 'a', encoding='utf-8', buffering=1) if args.logfile else io.TextIOWrapper(
        sys.stdout.buffer, encoding='utf-8', write_through=args.flush_logs)
    logging.basicConfig(
        level=loglevel,
        stream=stream,
        format='[%(asctime)s] %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

# ===========
# Token count
# ===========
def tokenize(text):
    return re.findall(r'\w+|\S', text)

def estimate_token_count(text):
    return len(tokenize(text))

# ========================
# Thread history retrieval
# ========================
def get_thread_history(post_id, max_posts, max_tokens, args):
    url = f"{args.mm_scheme}://{args.mm_url}:{args.mm_port}/api/v4/posts/{post_id}/thread"
    headers = {'Authorization': f'Bearer {args.bot_token}'}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()

    posts = sorted(resp.json()["posts"].values(), key=lambda p: p["create_at"])
    history = []
    total = 0
    for post in reversed(posts):
        count = estimate_token_count(post["message"])
        if max_posts and len(history) >= max_posts:
            break
        if total + count > max_tokens:
            break
        history.append((post["user_id"], post["message"]))
        total += count
    return list(reversed(history))

# ========================
# Mattermost + Flask setup
# ========================
def init_mattermost_driver(args):
    driver = Driver({
        "url": args.mm_url,
        "port": args.mm_port,
        "scheme": args.mm_scheme,
        "token": args.bot_token
    })
    driver.login()
    return driver

def create_app(args, mm_driver, mm_bot_id):
    app = Flask(__name__)
    app.config['ARGS'] = args

    @app.route('/webhook', methods=['POST'])
    def webhook():
        """Handle incoming webhook events from Mattermost."""
        logging.debug(f"Webhook received: {request.json}")

        data = request.json
        if data.get("token") != args.outgoing_webhook_token:
            return jsonify({'text': 'Invalid token'}), 403
        if data.get("user_id") == mm_bot_id:
            return jsonify({}), 200

        post_id = data["post_id"]
        channel_id = data["channel_id"]
        root_id = mm_driver.posts.get_post(post_id).get("root_id") or post_id

        additional_tokens = estimate_token_count(args.additional_message)
        thread = get_thread_history(root_id, args.max_thread_posts,
                                    args.max_thread_tokens - args.max_tokens - additional_tokens, args)

        messages = [{"role": "system", "content": args.system_message}]
        for user_id, msg in thread:
            role = "assistant" if user_id == mm_bot_id else "user"
            messages.append({"role": role, "content": msg})
        if messages and args.additional_message:
            messages[-1]["content"] += "\n" + args.additional_message

        # Send the request to OpenAI with retry on context_length_exceeded
        retry = True
        while retry:
            try:
                client = OpenAI(api_key=args.openai_api_key)
                response = client.chat.completions.create(
                    model=args.gpt_model,
                    messages=messages,
                    max_tokens=args.max_tokens,
                    temperature=args.temperature,
                    top_p=args.top_p,
                    frequency_penalty=args.frequency_penalty,
                    presence_penalty=args.presence_penalty
                )
                retry = False  # success
            except openai.BadRequestError as e:
                if "context_length_exceeded" in str(e).lower():
                    logging.info("Context length exceeded. Trimming oldest message and retrying...")
                    if len(messages) > 2:
                        messages.pop(1)  # Remove oldest user/assistant message (after system message)
                    else:
                        logging.error("Cannot reduce messages further. Aborting.")
                        raise e
                else:
                    raise e

        reply = response.choices[0].message['content']
        mm_driver.posts.create_post({
            'channel_id': channel_id,
            'message': reply,
            'root_id': root_id,
        })
        return jsonify({}), 200

    return app

# ==========
# Main logic
# ==========
if __name__ == '__main__':
    load_dotenv()
else:
    sys.argv = ['mattergpt']

args = parse_args()
client = OpenAI(api_key=args.openai_api_key)
configure_logging(args)

# removed: api_key no longer set globally = args.openai_api_key
mm_driver = init_mattermost_driver(args)
mm_bot_id = mm_driver.users.get_user('me')['id']
app = create_app(args, mm_driver, mm_bot_id)

if __name__ == '__main__':
    if args.gunicorn_path:
        subprocess.run([
            args.gunicorn_path,
            '--workers', str(args.workers),
            '--timeout', str(args.timeout),
            '--bind', f'{args.webhook_host}:{args.webhook_port}',
            'mattergpt:app'
        ])
    else:
        app.run(host=args.webhook_host, port=args.webhook_port, debug=args.debug)
