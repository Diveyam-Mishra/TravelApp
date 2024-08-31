from Schemas.PaymentSchemas import PaymentInformation
from Schemas.EventSchemas import SuccessResponse



async def CreateTransactionInDB(details: PaymentInformation, transactionContainer):
    query = "SELECT * FROM c WHERE c.transactionId = @transactionId"
    params = [{"name":"@transactionId", "value":details.transactionId}]

    items = list(transactionContainer.query_items(query=query, parameters=params, enable_cross_partition_query=True))

    if items:
        return SuccessResponse(message="Transaction is already in db", success=False)



    transactionContainer.create_item(details.to_dict())

    
    return SuccessResponse(message="Added transaction details in db", success=True)