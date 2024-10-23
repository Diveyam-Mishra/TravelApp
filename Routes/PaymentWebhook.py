from fastapi import APIRouter, Depends
from Schemas.PaymentSchemas import PaymentConfirmationRedirectBody,\
    PaymentInformation
import base64
import json
from Schemas.EventSchemas import SuccessResponse
from Database.Connection import get_successful_transaction_container
from Controllers.PaymentWebhook import CreateTransactionInDB
from Controllers.Auth import get_current_user
from fastapi.exceptions import HTTPException
from config import JWTBearer


router = APIRouter()


@router.post("/payment/redirect")
async def payment_redirect(
    body: PaymentConfirmationRedirectBody,
    transactionContainer = Depends(get_successful_transaction_container)
):
    encoded_data = body.response
    decoded_data = base64.b64decode(encoded_data)
    decoded_json = json.loads(decoded_data)
    status = decoded_json.get('success')

    if status != True:
        return SuccessResponse(message="Payment failed", success=False)

    newTransactionDetails=PaymentInformation(
        id=decoded_json["data"].get("merchantTransactionId"),
        transactionId=decoded_json["data"].get("merchantTransactionId"),
        data=decoded_json["data"]
    )

    # #print(newTransactionDetails)

    res = await CreateTransactionInDB(newTransactionDetails, transactionContainer)

    return res

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend

def load_public_key(filepath):
    with open(filepath, "rb") as key_file:
        public_key = serialization.load_pem_public_key(
            key_file.read(),
            backend=default_backend()
        )
    return public_key


@router.get("/encoded-data", dependencies=[Depends(JWTBearer())])
async def fetch_encoded_data(
    current_user = Depends(get_current_user)
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # The data to be encrypted
    data = {
        "paymentInfo": {
            "merchantId": "PGTESTPAYUAT86",
            "packageName": "com.example.phone_pe_demo",
            "appId": "",
            "environment": "SANDBOX"
        }
    }
    
    # Convert data to JSON and then to bytes
    data_bytes = json.dumps(data).encode('utf-8')
    
    # Load the public key
    public_key = load_public_key("./Secure/public_key.pem")
    
    # Encrypt the data
    encrypted_data = public_key.encrypt(
        data_bytes,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    
    # Encode the encrypted data in base64 to send as a string
    encrypted_data_base64 = base64.b64encode(encrypted_data).decode('utf-8')
    
    return {"encoded_data": encrypted_data_base64}