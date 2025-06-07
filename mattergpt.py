#!/usr/bin/env python3

# MatterGPT (mattergpt.py) version 1.1.0
# Entirely written and revised with ChatGPT-4o
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
from openai import OpenAI, APIError

# Load environment variables only when script is directly executed
if __name__ == "__main__":
    load_dotenv()
else:
    sys.argv = ['mattergpt']  # Needed for gunicorn CLI parsing

# Define and parse command-line arguments
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mm-url', default=os.environ.get('MATTERGPT_MM_URL', 'localhost'))
    parser.add_argument('--mm-port', type=int, default=os.environ.get('MATTERGPT_MM_PORT', 443))
    parser.add_argument('--mm-scheme', default=os.environ.get('MATTERGPT_MM_SCHEME', 'https'))
    parser.add_argument('--webhook-host', default=os.environ.get('MATTERGPT_WEBHOOK_HOST', '0.0.0.0'))
    parser.add_argument('--webhook-port', type=int, default=os.environ.get('MATTERGPT_WEBHOOK_PORT', 5000))
    parser.add_argument('--gpt-model', default=os.environ.get('MATTERGPT_GPT_MODEL', 'gpt-3.5-turbo'))
    parser.add_argument('--openai-api-key', default=os.environ.get('MATTERGPT_OPENAI_API_KEY'))
    parser.add_argument('--bot-token', default=os.environ.get('MATTERGPT_BOT_TOKEN'))
    parser.add_argument('--outgoing-webhook-token', default=os.environ.get('MATTERGPT_OUTGOING_WEBHOOK_TOKEN'))
    parser.add_argument('--system-message', default=os.environ.get('MATTERGPT_SYSTEM_MESSAGE', 'You are ChatGPT, a large language model trained by OpenAI.'))
    parser.add_argument('--additional-message', default=os.environ.get('MATTERGPT_ADDITIONAL_MESSAGE', ''))
    parser.add_argument('--logfile', default=os.environ.get('MATTERGPT_LOGFILE'))
    parser.add_argument('--loglevel', default=os.environ.get('MATTERGPT_LOGLEVEL', 'INFO'))
    parser.add_argument('--max-tokens', type=int, default=int(os.environ.get('MATTERGPT_MAX_TOKENS', 1000)))
    parser.add_argument('--temperature', type=float, default=float(os.environ.get('MATTERGPT_TEMPERATURE', 0.5)))
    parser.add_argument('--top-p', type=float, default=float(os.environ.get('MATTERGPT_TOP_P', 1.0)))
    parser.add_argument('--frequency-penalty', type=float, default=float(os.environ.get('MATTERGPT_FREQUENCY_PENALTY', 0.0)))
    parser.add_argument('--presence-penalty', type=float, default=float(os.environ.get('MATTERGPT_PRESENCE_PENALTY', 0.0)))
    parser.add_argument('--max-thread-posts', type=int, default=int(os.environ.get('MATTERGPT_MAX_THREAD_POSTS', 0)))
    parser.add_argument('--max-thread-tokens', type=int, default=int(os.environ.get('MATTERGPT_MAX_THREAD_TOKENS', 4096)))
    parser.add_argument('--debug', action='store_true', default=os.environ.get('MATTERGPT_DEBUG', 'false').lower() == 'true')
    parser.add_argument('--flush-logs', action='store_true', default=os.environ.get('MATTERGPT_FLUSH_LOGS', 'false').lower() == 'true')
    parser.add_argument('--gunicorn-path', default=os.environ.get('MATTERGPT_GUNICORN_PATH'))
    parser.add_argument('--workers', type=int, default=int(os.environ.get('MATTERGPT_WORKERS', 1)))
    parser.add_argument('--timeout', type=int, default=int(os.environ.get('MATTERGPT_TIMEOUT', 30)))
    return parser.parse_args()

# Utility to estimate token count using simple whitespace tokenizer
def estimate_token_count(text):
    return len(re.findall(r'\w+|\S', text or ''))

# Logging setup
def configure_logging(args):
    level = getattr(logging, args.loglevel.upper(), logging.INFO)
    stream = open(args.logfile, 'a', encoding='utf-8', buffering=1 if args.flush_logs else -1) if args.logfile else io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=args.flush_logs)
    logging.basicConfig(stream=stream, level=level, format="[%(asctime)s] %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

# Mattermost driver initialization
def init_mattermost_driver(args):
    driver = Driver({'url': args.mm_url, 'port': args.mm_port, 'scheme': args.mm_scheme, 'token': args.bot_token})
    driver.login()
    return driver

# Fetch thread history from Mattermost
def get_thread_history(post_id, args):
    url = f"{args.mm_scheme}://{args.mm_url}:{args.mm_port}/api/v4/posts/{post_id}/thread"
    headers = {"Authorization": f"Bearer {args.bot_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch thread history: {response.status_code} {response.text}")
    data = response.json()
    posts = sorted(data["posts"].values(), key=lambda x: x['create_at'])

    # Trim by token budget
    history = []
    tokens_used = estimate_token_count(args.additional_message)
    for post in reversed(posts):
        t = estimate_token_count(post["message"])
        if tokens_used + t > args.max_thread_tokens - args.max_tokens:
            break
        history.append((post["user_id"], post["message"]))
        tokens_used += t
    return list(reversed(history))

# Flask app factory
def create_app(args, mm_driver, mm_bot_id, client):
    app = Flask(__name__)
    @app.before_request
    def store_args(): g.args = args

    @app.route('/webhook', methods=['POST'])
    def webhook():
        args = g.args
        data = request.json
        if data.get('token') != args.outgoing_webhook_token:
            return jsonify({'text': 'Invalid token'}), 403
        if data.get('user_id') == mm_bot_id:
            return jsonify({}), 200

        post_id = data['post_id']
        root_id = mm_driver.posts.get_post(post_id).get("root_id") or post_id
        history = get_thread_history(root_id, args)

        messages = [{"role": "system", "content": args.system_message}]
        for uid, msg in history:
            role = "user" if uid != mm_bot_id else "assistant"
            if uid != mm_bot_id and args.additional_message:
                msg += f"{args.additional_message}"
            messages.append({"role": role, "content": msg})

        retry = True
        while retry:
            try:
                response = client.chat.completions.create(
                    model=args.gpt_model,
                    messages=messages,
                    max_tokens=args.max_tokens,
                    temperature=args.temperature,
                    top_p=args.top_p,
                    frequency_penalty=args.frequency_penalty,
                    presence_penalty=args.presence_penalty,
                )
                generated = response.choices[0].message.content
                retry = False
            except APIError as e:
                if "context_length_exceeded" in str(e):
                    messages.pop(1)
                    continue
                raise

        mm_driver.posts.create_post({
            'channel_id': data['channel_id'],
            'message': generated,
            'root_id': root_id,
        })
        return jsonify({}), 200

    return app

# Main entry
args = parse_args()
configure_logging(args)
client = OpenAI(api_key=args.openai_api_key)
mm_driver = init_mattermost_driver(args)
mm_bot_id = mm_driver.users.get_user('me')['id']

if __name__ == "__main__":
    if args.gunicorn_path:
        subprocess.run([args.gunicorn_path, "--workers", str(args.workers), "--timeout", str(args.timeout), "--bind", f"{args.webhook_host}:{args.webhook_port}", "mattergpt:app"])
    else:
        app = create_app(args, mm_driver, mm_bot_id, client)
        app.run(host=args.webhook_host, port=args.webhook_port, debug=args.debug)
elif __name__ == "mattergpt":
    app = create_app(args, mm_driver, mm_bot_id, client)
