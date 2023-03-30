#!/usr/bin/env python3

import os
import argparse
import logging
import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from mattermostdriver import Driver
import openai as OpenAI

app = Flask(__name__)
load_dotenv()

# Load environment variables
MATTERMOST_OUTGOING_WEBHOOK_TOKEN = os.environ['MATTERMOST_OUTGOING_WEBHOOK_TOKEN']
MATTERMOST_BOT_TOKEN = os.environ['MATTERMOST_BOT_TOKEN']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']

# Set up OpenAI API
OpenAI.api_key = OPENAI_API_KEY

def get_thread_history(post_id, max_thread_posts, mattermost_url, mattermost_port, mattermost_scheme):
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
    data = request.json
    token = data.get('token')

    if token != MATTERMOST_OUTGOING_WEBHOOK_TOKEN:
        return jsonify({'text': 'Invalid token'}), 403

    user_id = data.get('user_id')
    if user_id == mm_bot_id:
        return jsonify({}), 200

    post_id = data.get('post_id')
    channel_id = data.get('channel_id')
    message = data.get('text')

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

    # Add the incoming message from the user
    messages.append({"role": "user", "content": message})

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

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mm-url', default='localhost', help='Mattermost server URL')
    parser.add_argument('--mm-port', type=int, default=443, help='Mattermost server port')
    parser.add_argument('--mm-scheme', default='https', help='Mattermost server scheme (http or https)')
    parser.add_argument('--webhook-port', type=int, default=5000, help='Webhook listening port')
    parser.add_argument('--gpt-model', default='gpt-3.5-turbo', help='OpenAI ChatGPT model')
    parser.add_argument('--logfile', help='Path to log file (default: stdout)')
    parser.add_argument('--loglevel', default='INFO', help='Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
    parser.add_argument('--max-tokens', type=int, default=100, help='Maximum tokens for the generated text')
    parser.add_argument('--temperature', type=float, default=0.5, help='Temperature for the generated text (higher values make the output more diverse, lower values make it more conservative)')
    parser.add_argument('--max-thread-posts', type=int, default=20, help='Maximum number of posts to fetch in a thread')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode for Flask')
    args = parser.parse_args()

    loglevel = getattr(logging, args.loglevel.upper(), logging.INFO)
    logging.basicConfig(filename=args.logfile, level=loglevel)

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

    app.run(host='0.0.0.0', port=args.webhook_port, debug=args.debug)
