from flask import Blueprint, request, jsonify
import os
import logging

# Create blueprint
webhook_bp = Blueprint('webhook', __name__)

# Module logger
logger = logging.getLogger(__name__)

# Verify token for Facebook webhook verification
VERIFY_TOKEN = os.environ.get('FACEBOOK_VERIFY_TOKEN', 'my_secret_token')

@webhook_bp.route('/webhook', methods=['GET'])
def verify_webhook():
    """
    Handle the webhook verification from Facebook.
    Facebook will send a GET request with hub.verify_token and hub.challenge.
    We need to verify the token and return the challenge.
    """
    # Get parameters from the request
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    # Check if mode and token are in the request
    if mode and token:
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            logger.info('Webhook verified!')
            return challenge
        else:
            return 'Forbidden', 403
    return 'Bad Request', 400

@webhook_bp.route('/webhook', methods=['POST'])
def webhook():
    """
    Handle incoming webhook events from Facebook.
    This endpoint will receive updates about group activities.
    """
    data = request.get_json()
    logger.info(f'Received webhook data: {data}')

    # For now, just log the data and return success
    # TODO: Implement proper handling of different event types
    
    return jsonify({'status': 'ok'}), 200 