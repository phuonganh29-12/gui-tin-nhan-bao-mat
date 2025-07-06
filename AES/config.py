import os

# Configuration settings
HOST = 'localhost'
PORT = 12345
KEY_DIR = 'keys'

# Ensure key directory exists
if not os.path.exists(KEY_DIR):
    os.makedirs(KEY_DIR)

# File paths for RSA keys
ALICE_PRIVATE_KEY = os.path.join(KEY_DIR, 'alice_private.pem')
ALICE_PUBLIC_KEY = os.path.join(KEY_DIR, 'alice_public.pem')
BOB_PRIVATE_KEY = os.path.join(KEY_DIR, 'bob_private.pem')
BOB_PUBLIC_KEY = os.path.join(KEY_DIR, 'bob_public.pem')