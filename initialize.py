from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from azure.cosmos import CosmosClient, PartitionKey, exceptions

app = FastAPI()

COSMOS_DB_ENDPOINT = "https://trabii.documents.azure.com:443/"
COSMOS_DB_KEY = "qELt4gIxsjvhCg09o2jU9Msbaw9VNnHdrvo7RkXNKkWOeIJzrrRMLgSDb4ZDv8kD0RmyDkbHtOcPACDbsBvy5g=="
DATABASE_NAME = "eventsdb"
CONTAINER_NAME = "eventcontainer"

client = CosmosClient(COSMOS_DB_ENDPOINT, COSMOS_DB_KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

class Event(BaseModel):
    id: str
    name: str
    description: str
    date: str

@app.post("/events", status_code=201)
async def create_event(event: Event):
    try:
        container.create_item(event.dict())
        return {"message": "Event created successfully"}
    except exceptions.CosmosResourceExistsError:
        raise HTTPException(status_code=409, detail="Event already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))