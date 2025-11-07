"""
Configuration et constantes pour le backend pilot
"""

import os
import configparser


def load_config():
    """Charge la configuration depuis config.ini"""
    config = configparser.ConfigParser()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.ini")
    config.read(config_path)
    return config


# Charger la configuration globale
GLOBAL_CONFIG = load_config()


def get_consumer_config():
    """Retourne la configuration du consumer Kafka pour le pilot"""
    config = {
        'bootstrap.servers': GLOBAL_CONFIG.get('DEFAULT', 'bootstrap_servers'),
        'group.id': GLOBAL_CONFIG.get('DEFAULT', 'group_id_pilot'),
        'auto.offset.reset': 'earliest',
        'fetch.min.bytes': 1,
        'session.timeout.ms': 30000,
        'heartbeat.interval.ms': 3000,
        'max.poll.interval.ms': 300000,
    }
    
    # Ajouter la sécurité si configurée
    security_protocol = GLOBAL_CONFIG.get('DEFAULT', 'security_protocol', fallback='PLAINTEXT')
    config['security.protocol'] = security_protocol
    
    if security_protocol == 'SASL_SSL':
        config.update({
            'sasl.username': GLOBAL_CONFIG.get('DEFAULT', 'sasl_username'),
            'sasl.password': GLOBAL_CONFIG.get('DEFAULT', 'sasl_password'),
            'sasl.mechanism': 'PLAIN',
        })
    
    return config


def get_producer_config():
    """Retourne la configuration du producer Kafka pour le pilot"""
    config = {
        'bootstrap.servers': GLOBAL_CONFIG.get('DEFAULT', 'bootstrap_servers'),
        'acks': 'all',
        'retries': 3,
        'retry.backoff.ms': 300,
        'linger.ms': 10,
        'batch.size': 16384,
        'compression.type': 'snappy',
    }
    
    # Ajouter la sécurité si configurée
    security_protocol = GLOBAL_CONFIG.get('DEFAULT', 'security_protocol', fallback='PLAINTEXT')
    config['security.protocol'] = security_protocol
    
    if security_protocol == 'SASL_SSL':
        config.update({
            'sasl.username': GLOBAL_CONFIG.get('DEFAULT', 'sasl_username'),
            'sasl.password': GLOBAL_CONFIG.get('DEFAULT', 'sasl_password'),
            'sasl.mechanism': 'PLAIN',
        })
    
    return config


# Topics par défaut
INSTRUCTION_TOPIC = GLOBAL_CONFIG.get('DEFAULT', 'topic_to_consume', fallback='alex_training_instructions')
CHECKPOINT_TOPIC = GLOBAL_CONFIG.get('DEFAULT', 'topic_to_produce', fallback='alex_training_checkpoint')