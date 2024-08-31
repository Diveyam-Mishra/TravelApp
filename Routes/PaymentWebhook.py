from fastapi import APIRouter, Depends
from Schemas.PaymentSchemas import PaymentConfirmationRedirectBody,\
    PaymentInformation
import base64
import json
from Schemas.EventSchemas import SuccessResponse
from Database.Connection import get_booking_container,\
    get_successful_transaction_container
from Controllers.PaymentWebhook import CreateTransactionInDB


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
        id=decoded_json["data"].get("transactionId"),
        transactionId=decoded_json["data"].get("transactionId"),
        data=decoded_json["data"]
    )

    # print(newTransactionDetails)

    res = await CreateTransactionInDB(newTransactionDetails, transactionContainer)

    return res
    
    




