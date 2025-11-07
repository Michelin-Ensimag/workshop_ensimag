"""
Service Kafka pour la gestion des messages du pilote
"""

import asyncio
import json
import socket
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable

from confluent_kafka import Consumer, KafkaError, KafkaException, Producer
from pydantic import BaseModel

from config import get_consumer_config, get_producer_config, GLOBAL_CONFIG, INSTRUCTION_TOPIC, CHECKPOINT_TOPIC


class Instruction(BaseModel):
    """Modèle de validation pour une instruction"""
    id: str
    type: str
    action: str
    target: str
    km_gain: float
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class Checkpoint(BaseModel):
    """Modèle de validation pour un checkpoint"""
    type: str
    step: str
    id: str
    group_id: str
    km_travelled: float


class Ready(BaseModel):
    """Modèle de validation pour un message Ready"""
    type: str
    group_id: str
    message: str


class KafkaPilotService:
    """Service de gestion Kafka pour le pilote"""
    
    def __init__(self):
        # Logger pour écrire des messages dans l'interface
        self.logger = None
        # Store the main event loop for use in background threads
        self._main_loop = None
        # Flag to track if we've warned about logging issues
        self._logged_warning = False
        
        # État global de l'application
        self.current_status = "IDLE"  # IDLE, READY, DRIVING, COMPLETED
        self.status_lock = threading.Lock()
        
        # Configuration consumer et producer depuis config.ini
        self.consumer_conf = get_consumer_config()
        self.producer_conf = get_producer_config()
        
        # Données du pilote
        self.instructions: List[Dict] = []
        self.instruction_counter = 0
        self.total_km_travelled = 0.0
        self.checkpoints: Dict[str, asyncio.Event] = {}
        self.pending_commits: Dict[str, any] = {}
        
        # État de consommation
        self.running = False
        self.ready_sent = False
        self.consumer = None
        self.producer = None
        
        # Callback pour notifier le frontend
        self.instruction_callback: Optional[Callable] = None
        
        # Données de test pour simulation
        self.test_instructions = [
            {
                "id": "1",
                "type": "instruction",
                "action": "start",
                "target": "Départ - Place Grenette",
                "km_gain": 0.0,
                "latitude": 45.1885,
                "longitude": 5.7245
            },
            {
                "id": "2",
                "type": "instruction", 
                "action": "go_forward",
                "target": "Rue de la République",
                "km_gain": 0.2,
                "latitude": 45.1895,
                "longitude": 5.7255
            },
            {
                "id": "3",
                "type": "instruction",
                "action": "turn_right", 
                "target": "Boulevard Edouard Rey",
                "km_gain": 0.15,
                "latitude": 45.1905,
                "longitude": 5.7265
            },
            {
                "id": "4",
                "type": "instruction",
                "action": "go_forward",
                "target": "Avenue Alsace Lorraine",
                "km_gain": 0.3,
                "latitude": 45.1920,
                "longitude": 5.7280
            },
            {
                "id": "5",
                "type": "instruction",
                "action": "turn_left",
                "target": "Campus ENSIMAG",
                "km_gain": 0.25,
                "latitude": 45.1935,
                "longitude": 5.7295
            },
            {
                "id": "6",
                "type": "instruction",
                "action": "arrival",
                "target": "Arrivée - ENSIMAG",
                "km_gain": 0.1,
                "latitude": 45.1945,
                "longitude": 5.7305
            }
        ]
        self.test_instruction_index = 0
        
        self.log("✅ Kafka Pilot Service initialized successfully")

    def set_logger(self, logger_func):
        """Configure la fonction de logging"""
        self.logger = logger_func

    def log(self, message):
        """Log un message via le logger configuré ou print par défaut"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        if not self.logger:
            print(formatted_message)
            return
            
        try:
            # Try to get the current event loop (main thread case)
            try:
                loop = asyncio.get_running_loop()
                # We're in the main thread
                result = self.logger(formatted_message)
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
                return
            except RuntimeError:
                # No running loop - we're in a background thread
                pass
                
            # Background thread case - use the stored main loop
            if self._main_loop and self._main_loop.is_running():
                # Schedule the callback on the main loop
                future = asyncio.run_coroutine_threadsafe(
                    self.logger(formatted_message),
                    self._main_loop
                )
                # Optional: wait for a short time to ensure it's scheduled
                try:
                    future.result(timeout=0.1)
                except Exception:
                    # If it times out or fails, just print
                    print(formatted_message)
            else:
                # Fallback if no loop available
                print(formatted_message)
                
        except Exception as e:
            # Final fallback - at least print something
            print(f"[ERROR] Log failed: {e}")
            print(formatted_message)

    def set_instruction_callback(self, callback):
        """Configure le callback pour notifier le frontend des nouvelles instructions"""
        self.instruction_callback = callback

    def set_status(self, status):
        """Met à jour le statut global de manière thread-safe"""
        with self.status_lock:
            self.current_status = status
            self.log(f"🚁 Pilot Status updated: {status}")

    def get_status(self):
        """Récupère le statut global de manière thread-safe"""
        with self.status_lock:
            return self.current_status

    def test_connectivity(self):
        """Teste la connectivité au broker Kafka avec diagnostics avancés"""
        try:
            self.log("🔍 Testing Kafka connectivity...")
            
            # Test 1: Vérification réseau basique
            host, port = GLOBAL_CONFIG.get('DEFAULT', 'bootstrap_servers').split(':')
            port = int(port)
            
            self.log(f"🔗 Testing TCP connection to {host}:{port}...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                self.log("✅ TCP connection successful")
            else:
                self.log(f"❌ TCP connection failed with error code: {result}")
                return False
            
            # Test 2: Test producer simple
            self.log("🔍 Testing Kafka producer...")
            test_producer = Producer(self.producer_conf)
            
            def delivery_report(err, msg):
                if err is not None:
                    self.log(f"❌ Message delivery failed: {err}")
                else:
                    self.log(f"✅ Message delivered to {msg.topic()} [{msg.partition()}]")
            
            test_producer.produce(
                CHECKPOINT_TOPIC,
                key="test",
                value=json.dumps({"test": "connectivity"}),
                callback=delivery_report
            )
            test_producer.flush(timeout=10)
            
            # Test 3: Test consumer simple
            self.log("🔍 Testing Kafka consumer...")
            test_consumer = Consumer(self.consumer_conf)
            test_consumer.subscribe([INSTRUCTION_TOPIC])
            
            # Essayer de récupérer les métadonnées du topic
            metadata = test_consumer.list_topics(timeout=10)
            if INSTRUCTION_TOPIC in metadata.topics:
                self.log(f"✅ Topic {INSTRUCTION_TOPIC} found")
            else:
                self.log(f"⚠️ Topic {INSTRUCTION_TOPIC} not found, but connection works")
            
            test_consumer.close()
            
            self.log("✅ Kafka connectivity test passed")
            return True
            
        except Exception as e:
            self.log(f"❌ Kafka connectivity test failed: {str(e)}")
            return False

    async def send_ready_checkpoint(self):
        """Envoie le checkpoint ready pour démarrer la course"""
        if self.ready_sent:
            self.log("⚠️ Ready checkpoint already sent")
            return False
            
        try:
            if not self.producer:
                self.producer = Producer(self.producer_conf)
            
            ready_message = Ready(
                type="ready",
                group_id=self.consumer_conf['group.id'],
                message="Pilot ready to start driving"
            )
            
            def delivery_report(err, msg):
                if err is not None:
                    self.log(f"❌ Ready message delivery failed: {err}")
                else:
                    self.log(f"✅ Ready message delivered successfully")
                    print("✅ Ready message delivered successfully")
            
            self.producer.produce(
                CHECKPOINT_TOPIC,
                key=ready_message.group_id,
                value=ready_message.model_dump_json(),
                callback=delivery_report
            )
            
            self.producer.flush(timeout=10)
            self.ready_sent = True
            self.set_status("READY")
            print("🚀 Ready checkpoint sent successfully")
            
            # Démarrer la consommation de manière asynchrone SANS BLOQUER le retour
            asyncio.create_task(self.start_consumption())
            
            return True
            
        except Exception as e:
            self.log(f"❌ Failed to send ready checkpoint: {str(e)}")
            return False

    async def send_checkpoint(self, instruction_id: str, step: str):
        """Envoie un checkpoint pour une instruction donnée"""
        try:
            if not self.producer:
                self.producer = Producer(self.producer_conf)
            
            checkpoint = Checkpoint(
                type="checkpoint",
                step=step,
                id=instruction_id,
                group_id=self.consumer_conf['group.id'],
                km_travelled=self.total_km_travelled
            )
            
            def delivery_report(err, msg):
                if err is not None:
                    self.log(f"❌ Checkpoint delivery failed: {err}")
                else:
                    self.log(f"✅ Checkpoint {instruction_id} delivered")
            
            self.producer.produce(
                CHECKPOINT_TOPIC,
                key=checkpoint.group_id,
                value=checkpoint.model_dump_json(),
                callback=delivery_report
            )
            
            self.producer.flush(timeout=5)
            self.log(f"📍 Checkpoint sent for instruction {instruction_id}")
            
        except Exception as e:
            self.log(f"❌ Failed to send checkpoint: {str(e)}")

    async def start_consumption(self):
        """Démarre la consommation des messages Kafka ou la simulation"""
        if self.running:
            self.log("⚠️ Consumption already running")
            return
            
        self.running = True
        self.set_status("DRIVING")
        self.log("🎯 Starting instruction consumption...")
        
        # Run the blocking consumer in a thread executor
        try:
            loop = asyncio.get_running_loop()
            # Store the main loop for use in background threads
            self._main_loop = loop
            # Start the consumer loop in a background thread
            loop.run_in_executor(None, self._consume_kafka_instructions_blocking, loop)
        except RuntimeError as e:
            self.log(f"❌ Failed to start consumer: {e}")
            self.running = False
            self.set_status("IDLE")

    async def simulate_instruction_consumption(self):
        """Simule la consommation d'instructions avec les données de test"""
        self.log("🎮 Starting simulation mode with test instructions...")
        
        while self.running and self.test_instruction_index < len(self.test_instructions):
            instruction_data = self.test_instructions[self.test_instruction_index]
            
            try:
                # Valider l'instruction
                instruction = Instruction(**instruction_data)
                
                # Mettre à jour le kilométrage
                self.total_km_travelled += instruction.km_gain
                
                # Notifier le frontend
                if self.instruction_callback:
                    await self.instruction_callback(instruction_data)
                
                # Envoyer le checkpoint #TODO: id et step sont pour le moment identiques, à changer
                await self.send_checkpoint(instruction.id, instruction.id)
                
                self.log(f"📍 Processed instruction {instruction.id}: {instruction.action} -> {instruction.target}")
                
                self.test_instruction_index += 1
                
                # Attendre avant la prochaine instruction (simulation)
                await asyncio.sleep(3)
                
            except Exception as e:
                self.log(f"❌ Error processing test instruction: {str(e)}")
                break
        
        if self.test_instruction_index >= len(self.test_instructions):
            self.set_status("COMPLETED")
            self.log("🏁 All test instructions completed!")

    def _consume_kafka_instructions_blocking(self, loop: asyncio.AbstractEventLoop):
        """Blocking consumer loop to run in a thread executor.

        Args:
            loop: The asyncio event loop to schedule async callbacks on
        """
        try:
            print(f"[DEBUG] Creating consumer with config: {self.consumer_conf}")
            self.consumer = Consumer(self.consumer_conf)
            
            # Force manual partition assignment instead of subscribe
            from confluent_kafka import TopicPartition
            tp = TopicPartition(INSTRUCTION_TOPIC, 0, 0)  # topic, partition, offset
            print(f"[DEBUG] Manually assigning partition: {tp}")
            self.consumer.assign([tp])
            
            # Debug: check assigned partitions
            partitions = self.consumer.assignment()
            print(f"[DEBUG] Assigned partitions: {partitions}")
            
            self.log(f"📡 Started consuming from topic: {INSTRUCTION_TOPIC} partition 0")
            
            # Debug: Check topic metadata
            topics_metadata = self.consumer.list_topics(timeout=5)
            if INSTRUCTION_TOPIC in topics_metadata.topics:
                topic_meta = topics_metadata.topics[INSTRUCTION_TOPIC]
                print(f"[DEBUG] Topic metadata: partitions={len(topic_meta.partitions)}")
            else:
                print(f"[DEBUG] Warning: Topic {INSTRUCTION_TOPIC} not found in metadata!")
            
            poll_count = 0
            last_debug = time.time()
            
            while self.running:
                try:
                    current_time = time.time()
                    # Poll with a short timeout to allow checking running flag
                    msg = self.consumer.poll(timeout=1.0)
                    poll_count += 1
                    
                    # Print debug info every 5 seconds
                    if current_time - last_debug >= 5:
                        position = self.consumer.position(self.consumer.assignment())
                        print(f"[DEBUG] Consumer alive: polls={poll_count}, assigned={self.consumer.assignment()}, position={position}")
                        last_debug = current_time
                    
                    if msg is None:
                        continue
                    else: 
                        self.log(f"We got a message! {msg.value().decode('utf-8')}")    

                    if msg.error():
                        if msg.error().code() == KafkaError._PARTITION_EOF:
                            continue
                        else:
                            self.log(f"❌ Consumer error: {msg.error()}")
                            break

                    # Process message in the consumer thread
                    try:
                        instruction_data = json.loads(msg.value().decode('utf-8'))
                        instruction = Instruction(**instruction_data)
                        
                        # Update stats (thread-safe via locks if needed)
                        self.total_km_travelled += instruction.km_gain
                        
                        # Schedule async callbacks on the event loop
                        if self.instruction_callback:
                            asyncio.run_coroutine_threadsafe(
                                self.instruction_callback(instruction_data), 
                                loop
                            )
                        
                        # Schedule checkpoint send on the event loop
                        asyncio.run_coroutine_threadsafe(
                            self.send_checkpoint(instruction.id, instruction.id),
                            loop
                        )
                        
                        # Commit can happen in this thread
                        self.consumer.commit(msg)
                        
                        self.log(f"📍 Processed instruction {instruction.id}: {instruction.action}")
                        
                    except Exception as e:
                        self.log(f"❌ Error processing message: {str(e)}")
                        # Still commit to avoid reprocessing invalid messages
                        try:
                            self.consumer.commit(msg)
                        except:
                            pass
                        
                except Exception as e:
                    self.log(f"❌ Consumer loop error: {str(e)}")
                    # Small sleep to avoid tight error loop
                    time.sleep(0.5)
                    
        except Exception as e:
            self.log(f"❌ Fatal consumer error: {str(e)}")
        finally:
            if self.consumer:
                try:
                    self.consumer.close()
                except:
                    pass

    def stop_consumption(self):
        """Arrête la consommation des messages"""
        self.running = False
        self.set_status("IDLE")
        self.log("⏹️ Consumption stopped")

    def reset(self):
        """Remet à zéro l'état du service"""
        self.stop_consumption()
        self.ready_sent = False
        self.test_instruction_index = 0
        self.total_km_travelled = 0.0
        self.instruction_counter = 0
        self.instructions.clear()
        self.checkpoints.clear()
        self.pending_commits.clear()
        self.set_status("IDLE")
        self.log("🔄 Service reset completed")

    def get_stats(self):
        """Retourne les statistiques actuelles"""
        return {
            "status": self.get_status(),
            "ready_sent": self.ready_sent,
            "total_km_travelled": self.total_km_travelled,
            "instructions_processed": self.test_instruction_index,
            "total_instructions": len(self.test_instructions)
        }