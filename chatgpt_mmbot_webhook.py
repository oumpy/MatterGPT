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

    # Call OpenAI API
    response = OpenAI.Completion.create(
        engine=args.chat_gpt_model,
        prompt=f"{text}",
        max_tokens=100,
        n=1,
        stop=None,
        temperature=0.5,
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

    app.run(host='0.0.0.0', port=args.webhook_port, debug=True)
