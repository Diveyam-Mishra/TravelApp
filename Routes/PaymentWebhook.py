from fastapi import APIRouter, Depends, Body
from Schemas.PaymentSchemas import PaymentConfirmationRedirectBody,\
    PaymentInformation
import base64
import json
from Schemas.EventSchemas import SuccessResponse
from Database.Connection import get_successful_transaction_container, get_payment_init_container
from Controllers.PaymentWebhook import CreateTransactionInDB
from Controllers.Payments import saveTransactionInitInDB,generate_merchant_transaction_id, updateTransactionInitInDB
from Controllers.Auth import get_current_user
from fastapi.exceptions import HTTPException
from config import JWTBearer, settings
import secrets
import hashlib
import time
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


@router.post("/payment/razorpayHook")
async def payment_razorpay_hook(
    body: dict = Body(...),  # Accepts a JSON object
    paymentInitContainer=Depends(get_payment_init_container)
):
    # try:
    #     with open("webhook_payload.txt", "w") as file:
    #         json.dump(body, file, indent=4)
    #     print("Webhook payload saved to 'webhook_payload.txt'")
    # except Exception as e:
    #     print(f"Error saving webhook payload: {e}")
    #     raise HTTPException(
    #         status_code=500, 
    #         detail="Failed to save webhook payload"
    #     )
    print (body)
    event_type = body.get("event")
    account_id = body.get("account_id")
    payment_entity = body.get("payload", {}).get("payment", {}).get("entity", {})
    order_entity = body.get("payload", {}).get("order", {}).get("entity", {})
    print(order_entity)

    if not event_type or not order_entity:
        raise HTTPException(
            status_code=400, 
            detail="Invalid webhook payload: Missing event type or order details"
        )

    try:
        # Extract order details
        order_id = order_entity.get("id")
        status = order_entity.get("status")
        created_at = order_entity.get("created_at")  # Fallback to current UNIX time
        amount = order_entity.get("amount_paid")
        method=payment_entity.get("method")

        print(created_at)
        # Log received data (useful for debugging)
        print(f"Webhook received: Event Type - {event_type}, Order ID - {order_id}, Status - {status}")

        # Call the update function to update the transaction in the database
        update_result = await updateTransactionInitInDB(
            merchantId=order_id,  # Assuming `order_id` corresponds to the merchant ID
            paymentInitContainer=paymentInitContainer,
            status=status,
            amount=amount,
            method=method
        )

        return {"status": "success", "message": "Transaction updated successfully", "update_result": update_result}

    except Exception as e:
        print(f"Error handling Razorpay webhook: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing webhook: {str(e)}"
        )


@router.get("/getMerchantId", dependencies=[Depends(JWTBearer())])
async def getMerchantId(id_no: int, current_user=Depends(get_current_user), payment_init_container = Depends(get_payment_init_container)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    userId = current_user.id
    
    finalMerchantId = generate_merchant_transaction_id(userId, id_no)

    await saveTransactionInitInDB(userId, finalMerchantId, payment_init_container)

    return finalMerchantId

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
            # "merchantId": "PGTESTPAYUAT86",
            # "packageName": "com.example.phone_pe_demo",
            # "appId": "",
            # "environment": "SANDBOX"
            "razorpay_key":settings.RAZORPAY_KEY
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