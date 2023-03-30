import os
import argparse
import logging
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from mattermostdriver import Driver
from openai import OpenAI

app = Flask(__name__)
load_dotenv()

# Set up OpenAI API
OpenAI.api_key = os.environ['OPENAI_API_KEY']

def get_thread_history(channel_id, post_id):
    posts = mm_driver.posts.get_posts_for_channel(channel_id, since=post_id)
    thread_history = []

    for post in posts['posts'].values():
        if post['root_id'] == post_id:
            thread_history.append((post['user_id'], post['message']))

    return thread_history

def build_prompt(thread_history, message):
    conversation = ""

    for user_id, text in thread_history:
        if user_id == os.environ['BOT_USER_ID']:
            user = "ChatGPT"
        else:
            user = "User"

        conversation += f"{user}: {text}\n"

    conversation += f"User: {message}"
    return conversation

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    token = data.get('token')

    # Verify the webhook token
    if token != os.environ['OUTGOING_WEBHOOK_TOKEN']:
        return jsonify({'error': 'Invalid token'}), 403

    text = data['text']
    channel_id = data['channel_id']
    post_id = data['post_id']

    # Get thread history
    thread_history = get_thread_history(channel_id, post_id)

    # Build the prompt
    prompt = build_prompt(thread_history, text)

    # Call OpenAI API
    response = OpenAI.Completion.create(
        model=args.chat_gpt_model,
        prompt=prompt,
        max_tokens=args.max_tokens,
        n=1,
        stop=None,
        temperature=args.temperature,
    )

    reply = response.choices[0].text.strip()

    # Send reply to Mattermost in a thread
    mm_driver.posts.create_post({
        'channel_id': channel_id,
        'message': reply,
        'root_id': post_id
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
        'token': os.environ['BOT_USER_TOKEN'],
    })

    mm_driver.login()

    # Get bot user ID
    os.environ['BOT_USER_ID'] = mm_driver.users.get_user('me')['id']

    app.run(host='0.0.0.0', port=args.webhook_port, debug=True)
