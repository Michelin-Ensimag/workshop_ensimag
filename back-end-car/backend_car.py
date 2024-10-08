import asyncio
import configparser

import uvicorn
from confluent_kafka import Consumer, KafkaException, Producer, KafkaError, TopicPartition
from fastapi import FastAPI
from pydantic import BaseModel
import json


class KafkaManager:
    def __init__(self, config):
        self.config = config
        self.producer = self.initialize_producer()
        self.consumer = self.initialize_consumer()
        self.instructions = []
        self.instruction_counter = 0
        self.checkpoints = {}
        self.pending_commits = {}

    def initialize_consumer(self):
        consumer = Consumer(
            {
                "bootstrap.servers": self.config['DEFAULT']['bootstrap_servers'],
                "group.id": self.config['DEFAULT']['group_id'],
                "security.protocol": "SASL_SSL",
                "sasl.username": self.config['DEFAULT']['sasl_username'],
                "sasl.password": self.config['DEFAULT']['sasl_password'],
                "sasl.mechanism": "PLAIN",
                "auto.offset.reset": "earliest",
                "fetch.min.bytes": 1,
                "enable.auto.commit": False,
            },
        )
        consumer.subscribe(["tkfegbl1.training_instructions"])
        return consumer

    def initialize_producer(self):
        return Producer(
            {
                "bootstrap.servers": self.config['DEFAULT']['bootstrap_servers'],
                "security.protocol": "SASL_SSL",
                "sasl.username": self.config['DEFAULT']['sasl_username'],
                "sasl.password": self.config['DEFAULT']['sasl_password'],
                "sasl.mechanism": "PLAIN",
                "acks": "all",
            },
        )

    def delivery_report(self, err, msg):
        """Called once for each message produced to indicate delivery result."""
        if err is not None:
            print(f"Message delivery failed: {err}")
        else:
            print(f"Message delivered to {msg.topic()} [{msg.partition()}]")

    async def consume(self):
        """Asynchronous function to consume every 0.5 seconds using consumer configurations."""

    async def wait_for_checkpoint(self, step):
        """Wait for the checkpoint event and commit the message."""
        await self.checkpoints[step].wait()
        msg = self.pending_commits.pop(step)
        self.consumer.commit(msg, asynchronous=False)
        print(f"Committed message for step: {step}")

    async def produce(self, payload):
        """Asynchronous function to produce a message containing the payload."""
        # Trigger any available delivery report callbacks from previous produce() calls
        
        # Asynchronously produce a message. The delivery report callback will
        # be triggered from the call to poll() above, or flush() below, when the
        # message has been successfully delivered or failed permanently.
        
        # Mark the instruction as processed
        if payload.type == "checkpoint":
            print(f"Producing checkpoint for step: {payload.step}")
            if payload.step in self.checkpoints:
                self.checkpoints[payload.step].set()
            else:
                print(f"Warning: No instruction found for step: {payload.step}")


# Class used to receive payload for checkpoint
class Checkpoint(BaseModel):
    type: str
    step: str
    id: str
    group_id: str
    km_travelled: float

class Ready(BaseModel):
    type: str
    group_id: str
    message: str

# Global variables definition
is_started = 0
kafka_manager = None

# Instantiate application
app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Its called on application startup, to initialize consumer task."""
    global kafka_manager
    # Load configuration from a config.ini file
    config = configparser.ConfigParser()
    config.sections()
    config.read(['config.ini'])

    kafka_manager = KafkaManager(config)

    loop = asyncio.get_event_loop()
    loop.create_task(kafka_manager.consume())


@app.get("/instructions")
async def get_instructions():
    """Expose an /instruction endpoint to retrieve the value of all instructions."""
    return kafka_manager.instructions


@app.post('/ready')
async def ready():
    """Expose an endpoint called by the frontend to produce the ready message."""
    await kafka_manager.produce(Ready(type="ready", group_id=kafka_manager.config['DEFAULT']['group_id'],message="Ready to start the race"))
    return "Ready message sent"


@app.get("/next-instruction")
async def get_next_instruction():
    """Expose a /next-instruction endpoint to fetch instructions one by one."""
    # Warning : instructions can be polled in any order, you have to ensure each instructions will be processed in correct order.
    if len(kafka_manager.instructions) > kafka_manager.instruction_counter:
        next_instruction = kafka_manager.instructions[kafka_manager.instruction_counter]
        kafka_manager.instruction_counter += 1
        return next_instruction
    else:
        return None


@app.post("/checkpoint")
async def post_checkpoint(payload: Checkpoint):
    """Expose a /checkpoint endpoint to push checkpoint messages."""
    await kafka_manager.produce(payload)


def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
