#!/usr/bin/env python3
import os
import argparse
import logging
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from mattermostdriver import Driver
from openai import OpenAI

app = Flask(__name__)
load_dotenv()

# Load environment variables
OUTGOING_WEBHOOK_TOKEN = os.environ['OUTGOING_WEBHOOK_TOKEN']
BOT_USER_TOKEN = os.environ['BOT_USER_TOKEN']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']

# Set up OpenAI API
OpenAI.api_key = OPENAI_API_KEY

def get_thread_history(channel_id, post_id):
    posts = mm_driver.posts.get_posts_for_channel(channel_id, since=post_id)
    thread_history = []

    for post in posts['posts'].values():
        if post['root_id'] == post_id:
            thread_history.append((post['user_id'], post['message']))

    return thread_history

def build_prompt(thread_history, message, bot_user_id):
    messages = [
        (bot_user_id if user_id == bot_user_id else "user", msg)
        for user_id, msg in thread_history
    ]
    messages.append(("user", message))

    chat_history = "".join([f"{user}: {msg}\n" for user, msg in messages])
    prompt = f"{chat_history}ChatGPT:"
    return prompt

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    token = data.get('token')

    if token != OUTGOING_WEBHOOK_TOKEN:
        return jsonify({'text': 'Invalid token'}), 403

    user_id = data.get('user_id')
    if user_id == bot_user_id:
        return jsonify({}), 200

    post_id = data.get('post_id')
    channel_id = data.get('channel_id')
    message = data.get('text')

    # Get thread history
    thread_history = get_thread_history(channel_id, post_id)

    # Build the prompt
    prompt = build_prompt(thread_history, message, bot_user_id)

    # Generate a response using OpenAI API
    response = OpenAI.Completion.create(
        engine=args.chat_gpt_model,
        prompt=prompt,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        n=1,
        stop=["\n"]
    )

    # Extract the generated message
    generated_message = response.choices[0].text.strip()

    # Post the generated message as a reply in the thread
    mm_driver.posts.create_post({
        'channel_id': channel_id,
        'message': generated_message,
        'root_id': post_id,
    })

    return jsonify({}), 200

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mattermost-url', default='localhost', help='Mattermost server URL')
    parser.add_argument('--mattermost-port', type=int, default=443, help='Mattermost server port')
    parser.add_argument('--mattermost-scheme', default='https', help='Mattermost server scheme (http or https)')
    parser.add_argument('--webhook-port', type=int, default=5000, help='Webhook listening port')
    parser.add_argument('--chat-gpt-model', default='chat-gpt-3.5-turbo', help='OpenAI ChatGPT model')
    parser.add_argument('--logfile', help='Path to log file (default: stdout)')
    parser.add_argument('--loglevel', default='INFO', help='Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
    parser.add_argument('--max-tokens', type=int, default=100, help='Maximum tokens for the generated text')
    parser.add_argument('--temperature', type=float, default=0.5, help='Temperature for the generated text (higher values make the output more diverse, lower values make it more conservative)')
    args = parser.parse_args()

    loglevel = getattr(logging, args.loglevel.upper(), logging.INFO)
    logging.basicConfig(filename=args.logfile, level=loglevel)

    # Set up Mattermost driver
    mm_driver = Driver({
        'url': args.mattermost_url,
        'port': args.mattermost_port,
        'scheme': args.mattermost_scheme,
        'token': BOT_USER_TOKEN,
    })

    mm_driver.login()

    # Get bot user ID
    bot_user_id = mm_driver.users.get_user('me')['id']

    app.run(host='0.0.0.0', port=args.webhook_port, debug=True)
