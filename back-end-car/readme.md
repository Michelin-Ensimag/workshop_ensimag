# Backend Car

This project demonstrates how to do a basic Kafka implementation, with FastAPI to manage instructions and checkpoints for the racing game. 

Apache Kafka is a powerful tool used for building real-time data pipelines and streaming applications. Imagine it as a high-speed messaging system that allows different parts of a system to communicate with each other by sending and receiving messages.

Here’s a simple analogy: think of Kafka as a postal service. Just like how you send letters (messages) to different addresses (topics), Kafka allows applications to send messages (produced) to specific topics. These messages can then be read (consumed) by other applications that are interested in those topics.

Key points about Kafka:

- Publish and Subscribe: Applications can publish messages to Kafka topics, and other applications can subscribe to these topics to receive the messages.
- Scalability: Kafka is designed to handle large volumes of data and can scale horizontally by adding more servers.
- Durability: Messages in Kafka are stored on disk, making them durable and allowing them to be replayed if needed.
- Real-time Processing: Kafka enables real-time processing of data, making it ideal for applications that require immediate insights and actions.

In summary, Kafka is like a robust, high-speed postal service for data, enabling efficient and reliable communication between different parts of a system.

In this project, we will use the **confluent-kafka** python library to implement a producer and a consumer.

## Overview

This backend application will connect your front end (frontend_car project) and the admin server that will send race instructions. Its goal is to poll the instructions produced by the admin server, share them to the front end to process them, then produce a checkpoint message to acknowledge to the admin server the validation of the instruction.

On startup, the application will instantiate a `FastAPI` application and an instance of the `KafkaManager` class.

`FastAPI` is a framework designed to build APIs in python, its fast and easy to use. The framework is used to expose a few endpoints:

- GET /instructions : return all the instructions received by the backend.
- GET /next-instruction : return instructions one by one in order, used by the frontend to process each race instructions in order.
- POST /checkpoints : used to produce a checkpoint message, to validate that an instructions has been processed by the frontend.
- POST /ready : used at the beginning of the race to produce a ready message, to register your client to the admin server.

The `KafkaManager` class handles the connection to Kafka, producing and consuming messages asynchronously. The rest of the file is a FastAPI application that will expose some REST API endpoints for the frontend car project. The class is responsible for:

- Initializing Kafka producers and consumers.
- Consuming messages from a Kafka topic. The consumer will work as a asynchronous infinite loop, and it will populate the instructions collection each time it poll a new message.
- Producing messages to another Kafka topic. To produce ``ready`` and ``checkpoint`` messages for the admin server.
- Managing checkpoints to ensure messages are processed correctly. Each instructions received by the consumer will be attached to a checkpoint event in a coroutine. Each time the front end will send a checkpoint validation for a specific instruction, the associated event will trigger and end the coroutine. Finally the consumer will commit the message on the kafka broker side.

`Checkpoint` and `Ready` classes are used for data validation : it describes the required request body's format. 

## Getting Started

### Prerequisites

To ensure you'll have the required libraries, use the pip install command with the requirements.txt file.

```sh
pip install -r ./requirements.txt
```

### Launch the backend

```sh
python backend_car.py
```

Then you should have a FastAPI application startup, mentioning the backend is expose on a localhost IP address on port 8000.
The console will display logs about incoming and outgoing traffic.

### [ADVANCED] Backend car : Otel instrumentation

```sh
python3 -m venv venv
source ./venv/bin/activate

pip install opentelemetry-distro
pip install opentelemetry-exporter-otlp
pip install opentelemetry-exporter-otlp-proto
pip install opentelemetry-sdk
pip install opentelemetry-instrumentation


opentelemetry-bootstrap -a install

opentelemetry-instrument \
    --traces_exporter otlp \
    --metrics_exporter otlp \
    --logs_exporter console \
    --service_name "backend-car" \
    --exporter_otlp_endpoint "http://localhost:4242" \
    --exporter_otlp_protocol "http/protobuf" \
    python3 ./backend_car.py
```
