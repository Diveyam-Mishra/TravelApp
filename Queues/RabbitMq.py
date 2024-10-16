import aio_pika
import json
import asyncio
from collections import deque
from config import settings
# Global RabbitMQ connection and channel
rabbitmq_connection = None
channel = None

# Batching related configurations
batch_size = 10
batch_interval = 5  # seconds
message_batch = deque()
timeout_task = None  # To manage time-based batch sending

rabbit_mq_url = settings.RABBIT_MQ_URI

async def get_rabbitmq_channel():
    """
    Returns an existing RabbitMQ channel or creates a new one.
    Uses a global connection and channel to reuse across multiple requests.
    """
    global rabbitmq_connection, channel
    if not rabbitmq_connection:
        rabbitmq_connection = await aio_pika.connect_robust(rabbit_mq_url)
        channel = await rabbitmq_connection.channel()
    return channel

async def send_message_to_rabbitmq(queue_name: str, messages: list):
    """
    Sends a list of messages to the specified RabbitMQ queue.
    """
    channel = await get_rabbitmq_channel()
    message_body = json.dumps(messages)  # Serialize list of messages

    await channel.default_exchange.publish(
        aio_pika.Message(
            body=message_body.encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        ),
        routing_key=queue_name,
    )
    # print('sent')

async def batch_send_to_rabbitmq():
    """
    Sends the current batch of messages to RabbitMQ and clears the batch.
    This function should not be called directly but scheduled using add_send_ticket_data_to_batch.
    """
    global message_batch
    # print("check2")
    # print(len(message_batch))
    if len(message_batch) > 0:
        batched_messages = list(message_batch)  # Copy the batch
        message_batch.clear()  # Clear the batch after copying

        # Send the batched messages to RabbitMQ
        await send_message_to_rabbitmq('send_ticket_queue', batched_messages)

async def schedule_batch_send():
    """
    Schedules a batch to be sent after `batch_interval` seconds.
    Cancels the previous scheduled task if a new message comes in.
    """
    global timeout_task
    # If there is already a timeout scheduled, cancel it
    if timeout_task is not None:
        timeout_task.cancel()

    # Schedule a new task to send the batch after the interval
    timeout_task = asyncio.create_task(send_batch_after_timeout())
    # print("check1")

async def send_batch_after_timeout():
    """
    Waits for the specified batch interval and sends the batch if it has not reached the size.
    """
    await asyncio.sleep(batch_interval)
    await batch_send_to_rabbitmq()

async def add_send_ticket_data_to_batch(message: dict):
    """
    Adds a message to the batch. If the batch size is reached, it sends the messages immediately.
    Otherwise, it schedules the batch to be sent after a timeout (batch interval).
    """
    global message_batch

    # Add the message to the batch
    message_batch.append(message)

    # If the batch size is reached, send immediately
    if len(message_batch) >= batch_size:
        await batch_send_to_rabbitmq()
    else:
        # Schedule a batch send after the batch interval
        # print("check0")
        await schedule_batch_send()

# Optional: Shutdown function to close RabbitMQ connection gracefully
async def close_rabbitmq_connection():
    global rabbitmq_connection
    if rabbitmq_connection:
        await rabbitmq_connection.close()

