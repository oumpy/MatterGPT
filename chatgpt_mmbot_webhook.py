import os
import argparse
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from mattermostdriver import Driver
from openai import OpenAI

app = Flask(__name__)
load_dotenv()

# Set up OpenAI API
OpenAI.api_key = os.environ['OPENAI_API_KEY']

# Set up Mattermost driver
mm = Driver({
    'url': os.environ['MATTERMOST_URL'],
    'port': os.environ['MATTERMOST_PORT'],
    'scheme': os.environ['MATTERMOST_SCHEME'],
    'token': os.environ['BOT_USER_TOKEN'],
})

mm.login()


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    text = data['text']
    channel_id = data['channel_id']
    
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

    # Send reply to Mattermost
    mm.posts.create_post({
        'channel_id': channel_id,
        'message': reply
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
    args = parser.parse_args()

    if args.logfile:
        import logging
        logging.basicConfig(filename=args.logfile, level=logging.INFO)

    os.environ['MATTERMOST_URL'] = args.mattermost_url
    os.environ['MATTERMOST_PORT'] = str(args.mattermost_port)
    os.environ['MATTERMOST_SCHEME'] = args.mattermost_scheme

    app.run(host='0.0.0.0', port=args.webhook_port, debug=True)
