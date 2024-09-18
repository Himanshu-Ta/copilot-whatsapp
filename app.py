from flask import Flask, request, jsonify
from twilio.rest import Client
import requests
import json
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Retrieve credentials from environment variables
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
directline_token = os.getenv("DIRECTLINE_TOKEN")
twilio_whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")

# Initialize Twilio client
client = Client(account_sid, auth_token)

# DirectLine API URLs
directline_url = "https://directline.botframework.com/v3/directline/conversations"


# Function to create a DirectLine conversation
def create_conversation():
    headers = {
        "Authorization": f"Bearer {directline_token}",
        "Content-Type": "application/json",
    }
    response = requests.post(directline_url, headers=headers)
    conversation_id = response.json()["conversationId"]
    return conversation_id


# Function to send message to Copilot via DirectLine
def send_message_to_copilot(conversation_id, user_message):
    message_url = f"{directline_url}/{conversation_id}/activities"
    headers = {
        "Authorization": f"Bearer {directline_token}",
        "Content-Type": "application/json",
    }
    payload = {"type": "message", "from": {"id": "user"}, "text": user_message}
    response = requests.post(message_url, headers=headers, json=payload)
    return response.status_code


# Function to get the response from Copilot via DirectLine
def get_copilot_response(conversation_id):
    activities_url = f"{directline_url}/{conversation_id}/activities"
    headers = {
        "Authorization": f"Bearer {directline_token}",
        "Content-Type": "application/json",
    }
    response = requests.get(activities_url, headers=headers)
    activities = response.json().get("activities", [])

    if len(activities) > 1:
        return activities[-1].get("text", "Sorry, I didn’t understand that.")
    else:
        return "No response from Copilot."


# Webhook to handle incoming WhatsApp messages
@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_message = request.form.get("Body")
    from_number = request.form.get("From")

    print(f"Received a message from {from_number}: {incoming_message}")

    # Start conversation with Copilot via DirectLine
    conversation_id = create_conversation()

    # Send the user's message to Copilot
    send_message_to_copilot(conversation_id, incoming_message)

    # Get Copilot's response
    copilot_response = get_copilot_response(conversation_id)

    # Send Copilot's response back to the user via WhatsApp using Twilio
    send_whatsapp_message(from_number, copilot_response)

    return jsonify({"status": "success"}), 200


# Function to send a message via Twilio WhatsApp
def send_whatsapp_message(to, message):
    client.messages.create(body=message, from_=twilio_whatsapp_number, to=to)


# Run Flask app
if __name__ == "__main__":
    app.run(port=3003, debug=True)
