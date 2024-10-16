import aio_pika
import json
# Add the parent directory to the system path
from Schemas.PaymentSchemas import ticketData
from Database.Connection import get_db, get_container
from Controllers.Payments import send_ticket
from config import settings

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