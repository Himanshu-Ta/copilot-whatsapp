from flask import Flask, request, jsonify, send_from_directory
from twilio.rest import Client
import requests
import json
from dotenv import load_dotenv
import os
import logging

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Retrieve credentials from environment variables
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
directline_token = os.getenv("DIRECTLINE_TOKEN")
twilio_whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")

# Initialize Twilio client
client = Client(account_sid, auth_token)

# DirectLine API URLs
directline_url = "https://directline.botframework.com/v3/directline/conversations"

# Store conversation IDs for each user
user_conversations = {}

# Function to create a DirectLine conversation
def create_conversation():
    try:
        headers = {
            "Authorization": f"Bearer {directline_token}",
            "Content-Type": "application/json",
        }
        response = requests.post(directline_url, headers=headers)
        response.raise_for_status()
        conversation_id = response.json().get("conversationId")
        return conversation_id
    except requests.RequestException as e:
        logger.error(f"Error creating conversation: {e}")
        return None

# Function to send message to Copilot via DirectLine
def send_message_to_copilot(conversation_id, user_message):
    try:
        message_url = f"{directline_url}/{conversation_id}/activities"
        headers = {
            "Authorization": f"Bearer {directline_token}",
            "Content-Type": "application/json",
        }
        payload = {"type": "message", "from": {"id": "user"}, "text": user_message}
        response = requests.post(message_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.status_code
    except requests.RequestException as e:
        logger.error(f"Error sending message to Copilot: {e}")
        return None

# Function to get the response from Copilot via DirectLine
def get_copilot_response(conversation_id):
    try:
        activities_url = f"{directline_url}/{conversation_id}/activities"
        headers = {
            "Authorization": f"Bearer {directline_token}",
            "Content-Type": "application/json",
        }
        response = requests.get(activities_url, headers=headers)
        response.raise_for_status()
        activities = response.json().get("activities", [])

        if len(activities) > 1:
            return activities[-1].get("text", "Sorry, I didn’t understand that.")
        else:
            return "No response from Copilot."
    except requests.RequestException as e:
        logger.error(f"Error getting response from Copilot: {e}")
        return "Error retrieving response."

# Webhook to handle incoming WhatsApp messages
@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_message = request.form.get("Body")
    from_number = request.form.get("From")

    logger.info(f"Received a message from {from_number}: {incoming_message}")

    # Get or create a conversation ID for the user
    if from_number in user_conversations:
        conversation_id = user_conversations[from_number]
    else:
        conversation_id = create_conversation()
        if not conversation_id:
            return jsonify({"status": "error", "message": "Failed to create conversation"}), 500
        user_conversations[from_number] = conversation_id

    # Send the user's message to Copilot
    if send_message_to_copilot(conversation_id, incoming_message) != 200:
        return jsonify({"status": "error", "message": "Failed to send message to Copilot"}), 500

    # Get Copilot's response
    copilot_response = get_copilot_response(conversation_id)

    # Send Copilot's response back to the user via WhatsApp using Twilio
    send_whatsapp_message(from_number, copilot_response)

    return jsonify({"status": "success"}), 200

# Function to send a message via Twilio WhatsApp
def send_whatsapp_message(to, message):
    try:
        client.messages.create(body=message, from_=twilio_whatsapp_number, to=to)
    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {e}")

# Route for the root URL
@app.route("/", methods=["GET"])
def home():
    return "Welcome to the Flask app!"

# Route for favicon.ico
@app.route("/favicon.ico")
def favicon():
    return app.send_static_file("favicon.ico")

# Run Flask app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=3003, debug=True)
