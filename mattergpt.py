#!/usr/bin/env python3

# MatterGPT (mattergpt.py) version 1.1.0
# Entirely written and maintained with help from ChatGPT (GPT-4o)
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
from openai.error import OpenAIError


# Parse command-line arguments and set defaults from environment variables
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--openai-api-key', default=os.environ.get('MATTERGPT_OPENAI_API_KEY'), help='OpenAI API key')
    parser.add_argument('--bot-token', default=os.environ.get('MATTERGPT_BOT_TOKEN'), help='Mattermost bot token')
    parser.add_argument('--webhook-token', default=os.environ.get('MATTERGPT_OUTGOING_WEBHOOK_TOKEN'), help='Mattermost outgoing webhook token')
    parser.add_argument('--mm-url', default=os.environ.get('MATTERGPT_MM_URL', 'localhost'), help='Mattermost server URL')
    parser.add_argument('--mm-port', type=int, default=os.environ.get('MATTERGPT_MM_PORT', 443), help='Mattermost server port')
    parser.add_argument('--mm-scheme', default=os.environ.get('MATTERGPT_MM_SCHEME', 'https'), help='Mattermost server scheme (http or https)')
    parser.add_argument('--webhook-host', default=os.environ.get('MATTERGPT_WEBHOOK_HOST', '0.0.0.0'), help='Webhook listening host')
    parser.add_argument('--webhook-port', type=int, default=os.environ.get('MATTERGPT_WEBHOOK_PORT', 5000), help='Webhook listening port')
    parser.add_argument('--gpt-model', default=os.environ.get('MATTERGPT_GPT_MODEL', 'gpt-3.5-turbo'), help='OpenAI model name')
    parser.add_argument('--system-message', default=os.environ.get('MATTERGPT_SYSTEM_MESSAGE', 'You are ChatGPT, a large language model trained by OpenAI.'), help='System prompt')
    parser.add_argument('--additional-message', default=os.environ.get('MATTERGPT_ADDITIONAL_MESSAGE', ''), help='Message appended to last user message')
    parser.add_argument('--logfile', default=os.environ.get('MATTERGPT_LOGFILE', None), help='Log file path')
    parser.add_argument('--loglevel', default=os.environ.get('MATTERGPT_LOGLEVEL', 'INFO'), help='Log level')
    parser.add_argument('--max-tokens', type=int, default=int(os.environ.get('MATTERGPT_MAX_TOKENS', 1000)), help='Max tokens to generate')
    parser.add_argument('--temperature', type=float, default=float(os.environ.get('MATTERGPT_TEMPERATURE', 0.5)), help='Sampling temperature')
    parser.add_argument('--top-p', type=float, default=float(os.environ.get('MATTERGPT_TOP_P', 1.0)), help='Top-p sampling')
    parser.add_argument('--frequency-penalty', type=float, default=float(os.environ.get('MATTERGPT_FREQUENCY_PENALTY', 0.0)), help='Frequency penalty')
    parser.add_argument('--presence-penalty', type=float, default=float(os.environ.get('MATTERGPT_PRESENCE_PENALTY', 0.0)), help='Presence penalty')
    parser.add_argument('--max-thread-posts', type=int, default=int(os.environ.get('MATTERGPT_MAX_THREAD_POSTS', 0)), help='Max posts to include from thread (0=unlimited)')
    parser.add_argument('--max-thread-tokens', type=int, default=int(os.environ.get('MATTERGPT_MAX_THREAD_TOKENS', 4096)), help='Max tokens to include from thread history')
    parser.add_argument('--debug', action='store_true', default=str(os.environ.get('MATTERGPT_DEBUG', 'false')).lower() == 'true', help='Enable Flask debug mode')
    parser.add_argument('--flush-logs', action='store_true', default=str(os.environ.get('MATTERGPT_FLUSH_LOGS', 'false')).lower() == 'true', help='Flush logs immediately')
    parser.add_argument('--gunicorn-path', default=os.environ.get('MATTERGPT_GUNICORN_PATH'), help='Gunicorn executable path')
    parser.add_argument('--workers', type=int, default=int(os.environ.get('MATTERGPT_WORKERS', 1)), help='Gunicorn worker count')
    parser.add_argument('--timeout', type=int, default=int(os.environ.get('MATTERGPT_TIMEOUT', 30)), help='Gunicorn timeout seconds')

    return parser.parse_args()


# Configure root logger with formatting and output settings
def configure_logging(args):
    loglevel = getattr(logging, args.loglevel.upper(), logging.INFO)
    stream = open(args.logfile, 'a', encoding='utf-8', buffering=1) if args.logfile else io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=args.flush_logs)
    logging.basicConfig(stream=stream, level=loglevel, format='[%(asctime)s] %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')


# Estimate the token count using regular expressions for word-like segments
def estimate_token_count(text):
    return len(re.findall(r'\w+|\S', text))


def get_thread_history(post_id, max_posts, max_tokens, url, port, scheme, token):
    api_url = f"{scheme}://{url}:{port}/api/v4/posts/{post_id}/thread"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()

    posts = sorted(response.json()["posts"].values(), key=lambda x: x["create_at"])
    history, tokens = [], 0
    for post in reversed(posts):
        t = estimate_token_count(post["message"])
        if max_posts and len(history) >= max_posts:
            break
        if tokens + t > max_tokens:
            break
        history.append((post["user_id"], post["message"]))
        tokens += t
    return list(reversed(history))


# Create the Flask app with the webhook route
def create_app(args, mm_driver, mm_bot_id):
    app = Flask(__name__)
    @app.before_request
    def set_args(): g.args = args

    @app.route('/webhook', methods=['POST'])
    def webhook():
        args = g.args
        token = request.json.get('token')
        if token != args.webhook_token:
            return jsonify({'text': 'Invalid token'}), 403

        if request.json.get('user_id') == mm_bot_id:
            return jsonify({}), 200

        post_id = request.json['post_id']
        channel_id = request.json['channel_id']
        root_id = mm_driver.posts.get_post(post_id).get('root_id') or post_id

        buffer = args.max_tokens + estimate_token_count(args.additional_message)
        history = get_thread_history(root_id, args.max_thread_posts, args.max_thread_tokens - buffer,
                                     args.mm_url, args.mm_port, args.mm_scheme, args.bot_token)

        messages = [{"role": "system", "content": args.system_message}]
        for user, msg in history:
            role = "user" if user != mm_bot_id else "assistant"
            if user != mm_bot_id and msg == history[-1][1]:
                msg += f"\n{args.additional_message}"
            messages.append({"role": role, "content": msg})

        while True:
            try:
                resp = openai.ChatCompletion.create(
                    model=args.gpt_model,
                    messages=messages,
                    max_tokens=args.max_tokens,
                    temperature=args.temperature,
                    top_p=args.top_p,
                    frequency_penalty=args.frequency_penalty,
                    presence_penalty=args.presence_penalty,
                    api_key=args.openai_api_key
                )
                break
            except OpenAIError as e:
                if hasattr(e, 'error') and e.error.get('code') == 'context_length_exceeded':
                    logging.warning("Retrying with reduced messages")
                    messages.pop(1)
                else:
                    raise

        reply = resp.choices[0].message['content']
        mm_driver.posts.create_post({
            'channel_id': channel_id,
            'message': reply,
            'root_id': root_id
        })
        return jsonify({}), 200
    return app


if __name__ == '__main__':
    load_dotenv()
else:
    sys.argv = ['mattergpt']

args = parse_args()
configure_logging(args)
openai.api_key = args.openai_api_key
mm_driver = Driver({
    'url': args.mm_url,
    'port': args.mm_port,
    'scheme': args.mm_scheme,
    'token': args.bot_token,
})
mm_driver.login()
mm_bot_id = mm_driver.users.get_user('me')['id']

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
        app = create_app(args, mm_driver, mm_bot_id)
        app.run(host=args.webhook_host, port=args.webhook_port, debug=args.debug)
elif __name__ == 'mattergpt':
    app = create_app(args, mm_driver, mm_bot_id)