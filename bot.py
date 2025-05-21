from flask import Flask, request
import os
import openai
from slack_sdk import WebClient
from slack_sdk.signature import SignatureVerifier
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
app = Flask(__name__)

# Setup Slack + OpenAI clients
client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
verifier = SignatureVerifier(os.environ["SLACK_SIGNING_SECRET"])
openai.api_key = os.environ["OPENAI_API_KEY"]

# System prompt for GPT (2-line realness)
HOMIE_PROMPT = """
you are a slack bot that replaces pranav menon as a tks coach. your job is to challenge students to think deeper, reflect sharper, or take action — in less than 2 lines.

you never greet people. no 'hey', no 'what's up', no 'how are you'. you cut straight to the point. always speak in lowercase. never use gen-z slang or emojis. your tone is grounded, human, sometimes sharp, always real.

never sound like a chatbot. never ramble. no disclaimers. just say what matters. be useful or push the student to go further.
"""

# Avoid duplicate replies
processed_event_ids = set()

@app.route("/slack/events", methods=["POST"])
def slack_events():
    # Verify request
    if not verifier.is_valid_request(request.get_data(), request.headers):
        return "Invalid request", 403

    payload = request.get_json()
    event_id = payload.get("event_id")

    # Slack challenge check (initial verification)
    if payload.get("type") == "url_verification":
        return payload.get("challenge"), 200

    # Skip if already processed
    if event_id in processed_event_ids:
        return "Duplicate event", 200
    processed_event_ids.add(event_id)

    event = payload.get("event", {})
    if "bot_id" in event:
        return "Ignore bot message", 200

    # Only respond to top-level @mentions or DMs
    is_app_mention = event.get("type") == "app_mention" and not event.get("thread_ts")
    is_dm = event.get("channel_type") == "im"

    if is_app_mention or is_dm:
        user_message = event.get("text", "")
        channel_id = event.get("channel")

        # Ask GPT
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": HOMIE_PROMPT},
                {"role": "user", "content": user_message}
            ]
        )
        reply = response.choices[0].message.content.strip()

        # Reply in Slack
        client.chat_postMessage(channel=channel_id, text=reply)

    return "ok", 200
