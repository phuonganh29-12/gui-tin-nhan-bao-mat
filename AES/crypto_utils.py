import json
import base64
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
from Crypto.Random import get_random_bytes
import os
from config import ALICE_PRIVATE_KEY, ALICE_PUBLIC_KEY, BOB_PRIVATE_KEY, BOB_PUBLIC_KEY

def pad(data):
    padding_len = 16 - (len(data) % 16)
    return data + bytes([padding_len] * padding_len)

def unpad(data):
    padding_len = data[-1]
    return data[:-padding_len]

def generate_and_save_rsa_keys(user):
    key = RSA.generate(2048)
    private_key = key
    public_key = key.publickey()
    
    if user == "alice":
        with open(ALICE_PRIVATE_KEY, 'wb') as f:
            f.write(private_key.export_key())
        with open(ALICE_PUBLIC_KEY, 'wb') as f:
            f.write(public_key.export_key())
    elif user == "bob":
        with open(BOB_PRIVATE_KEY, 'wb') as f:
            f.write(private_key.export_key())
        with open(BOB_PUBLIC_KEY, 'wb') as f:
            f.write(public_key.export_key())
    
    return private_key, public_key

def load_rsa_keys(user):
    if user == "alice":
        private_path, public_path = ALICE_PRIVATE_KEY, ALICE_PUBLIC_KEY
    else:
        private_path, public_path = BOB_PRIVATE_KEY, BOB_PUBLIC_KEY
    
    if os.path.exists(private_path) and os.path.exists(public_path):
        with open(private_path, 'rb') as f:
            private_key = RSA.import_key(f.read())
        with open(public_path, 'rb') as f:
            public_key = RSA.import_key(f.read())
    else:
        private_key, public_key = generate_and_save_rsa_keys(user)
    
    return private_key, public_key

def encrypt_aes_key(aes_key, public_key):
    cipher_rsa = PKCS1_OAEP.new(public_key)
    return cipher_rsa.encrypt(aes_key)

def decrypt_aes_key(encrypted_aes_key, private_key):
    cipher_rsa = PKCS1_OAEP.new(private_key)
    return cipher_rsa.decrypt(encrypted_aes_key)

def sign_data(data, private_key):
    h = SHA256.new(data)
    signer = PKCS1_v1_5.new(private_key)
    return signer.sign(h)

def verify_signature(data, signature, public_key):
    h = SHA256.new(data)
    verifier = PKCS1_v1_5.new(public_key)
    return verifier.verify(h, signature)

def encrypt_message(message, aes_key):
    iv = get_random_bytes(16)
    cipher_aes = AES.new(aes_key, AES.MODE_CBC, iv)
    padded_message = pad(message.encode())
    ciphertext = cipher_aes.encrypt(padded_message)
    return iv, ciphertext

def decrypt_message(iv, ciphertext, aes_key):
    cipher_aes = AES.new(aes_key, AES.MODE_CBC, iv)
    padded_message = cipher_aes.decrypt(ciphertext)
    return unpad(padded_message).decode()

def compute_hash(iv, ciphertext):
    return SHA256.new(iv + ciphertext).hexdigest()