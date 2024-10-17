import aio_pika
import json
# Add the parent directory to the system path
from Schemas.PaymentSchemas import ticketData
from Controllers.Payments import send_ticket
from config import settings
from sqlalchemy.engine import URL
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from azure.cosmos import CosmosClient

Driver = settings.Driver
Server = settings.Server
Database = settings.Database
Uid = settings.Uid
SQLPwd = settings.SQLPwd

connection_string = f"DRIVER={Driver};SERVER={Server};DATABASE={Database};UID={Uid};PWD={SQLPwd}"
connection_url = URL.create("mssql+pyodbc", query={"odbc_connect": connection_string})
engine = create_engine(
    connection_url,
    pool_size=10,          # Minimum number of connections maintained in the pool
    max_overflow=20,       # Maximum number of connections beyond the pool_size
    pool_timeout=30,       # Timeout for acquiring a connection from the pool
    pool_recycle=1800,     # Recycle connections to avoid DB timeouts (in seconds)
    echo=False,            # Set to True if you want to see SQL queries in logs (for debugging)
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_container():
    yield container

COSMOS_DB_ENDPOINT = settings.COSMOS_DB_ENDPOINT
COSMOS_DB_KEY = settings.COSMOS_DB_KEY + "=="
DATABASE_NAME = settings.DATABASE_NAME 
CONTAINER_NAME = settings.CONTAINER_NAME
client = CosmosClient(COSMOS_DB_ENDPOINT, COSMOS_DB_KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

async def process_message(message: aio_pika.IncomingMessage):
    async with message.process():
        batch_messages = json.loads(message.body)
        for message_data in batch_messages:
            ticket_id = message_data["ticketId"]

            # Extract the ticket data from the message
            new_ticket_data = ticketData(
                eventId=message_data["eventId"],
                userId_O=message_data["userId_O"],
                paid_amount_O=message_data["paid_amount_O"],
                payment_id_O=message_data["payment_id_O"],
                members_details_O=message_data["members_details_O"]
            )

            # Call the ticket sending function asynchronously
            db = next(get_db())  # Get a database session
            eventContainer = next(get_container())  # Get the container

            response = await send_ticket(new_ticket_data, eventContainer, db, ticket_id)
            print(f"Ticket {ticket_id} processed: {response}")

async def main():
    rabbit_mq_url = settings.RABBIT_MQ_URI

    connection = await aio_pika.connect_robust(rabbit_mq_url)
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue('send_ticket_queue', durable=True)

        await queue.consume(process_message, no_ack=False)

        print('Waiting for messages. To exit press CTRL+C')
        await asyncio.Future()  # Run forever

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())