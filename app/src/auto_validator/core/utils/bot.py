import json

import redis


def trigger_bot_send_message(channel_name: str, message: str, realm: str):
    redis_client = redis.Redis(host='localhost', port=8379, db=0)
    command = {
        'action': 'send_message',
        'channel_name': channel_name,
        'message': message,
        'realm': realm
    }
    redis_client.publish('bot_commands', json.dumps(command))
