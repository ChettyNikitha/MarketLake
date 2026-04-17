# importing pythons built in datetime , to request access for kalshi demo data , everytime we trying to connect by request , it checks key id, key and timestamp to grant
import datetime
import base64 
# using serialization to load & read key file , hasinhg for privacy 
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
# credential to access kalshi demo
KEY_ID = "0ffe4e8a-dc39-48f3-badd-54360bd5d92e"
KEY_FILE = "kalshi-key.key"
BASE_URL = "https://demo-api.kalshi.co"

# func to load key , opening and reading file in binary(rb(raw bytes)) naming a skeyfile
def load_private_key():
    with open(KEY_FILE, "rb") as key_file:
        # converts rb to python key obeject , using cryoto engine to process 
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )
    return private_key
# signing on every api request with timstamp , used method and path to get acces from kalshi
def sign_request(method: str, path: str) -> dict:
    timestamp = str(int(datetime.datetime.now().timestamp() * 1000))
    message = timestamp + method + path

    private_key = load_private_key()
    signature = private_key.sign(
        # coverting string message to bytwe
        message.encode("utf-8"),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH
        ),
        hashes.SHA256()
    )
    # retuning headers for evry kalshi request
    return {
        "KALSHI-ACCESS-KEY": KEY_ID,
        "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode("utf-8"),
        "KALSHI-ACCESS-TIMESTAMP": timestamp,
        "Content-Type": "application/json"
    }