/**
 * Frontend JavaScript pour Backend Pilot
 * Gère la communication WebSocket, la carte Leaflet et l'interface utilisateur
 */

class BackendPilotApp {
    constructor() {
        this.ws = null;
        this.map = null;
        this.carMarker = null;
        this.currentPosition = [45.1885, 5.7245]; // Position de départ (Place Grenette, Grenoble)
        this.routePolyline = null;
        this.routePoints = [];
        this.isConnected = false;
        
        // Éléments DOM
        this.statusBadge = document.getElementById('status-badge');
        this.totalKm = document.getElementById('total-km');
        this.instructionCount = document.getElementById('instruction-count');
        this.currentInstructionContent = document.getElementById('current-instruction-content');
        this.logsContainer = document.getElementById('logs-container');
        this.connectivityStatus = document.getElementById('connectivity-status');
        
        // Boutons
        this.btnStartRace = document.getElementById('btn-start-race');
        this.btnStop = document.getElementById('btn-stop');
        this.btnReset = document.getElementById('btn-reset');
        this.btnTestConnectivity = document.getElementById('btn-test-connectivity');
        this.btnConfirmStart = document.getElementById('btn-confirm-start');
        this.btnCancelStart = document.getElementById('btn-cancel-start');
        
        // Modales
        this.startRaceModal = new bootstrap.Modal(document.getElementById('startRaceModal'));
        this.loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
        
        this.init();
    }
    
    async init() {
        console.log('🚀 Initializing Backend Pilot App...');
        
        // Afficher la modale de chargement
        this.showLoadingModal('Initialisation de la carte...');
        
        // Initialiser la carte
        this.initMap();
        
        // Configurer les événements
        this.setupEventListeners();
        
        // Attendre un peu puis se connecter
        setTimeout(() => {
            this.hideLoadingModal();
            this.connectWebSocket();
        }, 1000);
    }
    
    initMap() {
        console.log('🗺️ Initializing Leaflet map...');
        
        // Créer la carte centrée sur Grenoble
        this.map = L.map('map').setView(this.currentPosition, 13);
        
        // Ajouter les tiles OpenStreetMap
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.map);
        
        // Créer le marqueur de voiture de course personnalisé
        const raceCarIcon = L.divIcon({
            html: '<div style="font-size: 24px;">🏎️</div>',
            className: 'race-car-marker',
            iconSize: [24, 24],
            iconAnchor: [12, 12]
        });

        this.carMarker = L.marker(this.currentPosition, {
            icon: raceCarIcon
        }).addTo(this.map);
        
        this.carMarker.bindPopup('🏎️ Position de la voiture');
        
        // Initialiser la polyline pour le trajet
        this.routePolyline = L.polyline([], {
            color: '#007bff',
            weight: 4,
            opacity: 0.7
        }).addTo(this.map);
        
        console.log('✅ Map initialized successfully');
    }
    
    setupEventListeners() {
        console.log('⚙️ Setting up event listeners...');
        
        // Bouton démarrer la course
        this.btnStartRace.addEventListener('click', () => {
            this.startRaceModal.show();
        });
        
        // Confirmation démarrage
        this.btnConfirmStart.addEventListener('click', async () => {
            this.startRaceModal.hide();
            await this.startRace();
        });
        
        // Bouton arrêter
        this.btnStop.addEventListener('click', async () => {
            await this.stopService();
        });
        
        // Bouton reset
        this.btnReset.addEventListener('click', async () => {
            await this.resetService();
        });
        
        // Bouton test connectivité
        this.btnTestConnectivity.addEventListener('click', async () => {
            await this.testConnectivity();
        });
        
        // Auto-scroll des logs
        this.logsContainer.addEventListener('DOMNodeInserted', () => {
            this.logsContainer.scrollTop = this.logsContainer.scrollHeight;
        });
    }
    
    connectWebSocket() {
        console.log('🔌 Connecting to WebSocket...');
        this.updateConnectionStatus('connecting');

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('✅ WebSocket connected');
            this.isConnected = true;
            this.updateConnectionStatus('connected');
            this.addLog('🔌 Connexion WebSocket établie', 'success');
        };

        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                this.handleWebSocketMessage(message);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };

        this.ws.onclose = () => {
            console.log('❌ WebSocket disconnected');
            this.isConnected = false;
            this.updateConnectionStatus('disconnected');
            this.addLog('🔌 Connexion WebSocket fermée', 'error');

            // Tentative de reconnexion après 3 secondes
            setTimeout(() => {
                if (!this.isConnected) {
                    this.connectWebSocket();
                }
            }, 3000);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.addLog('❌ Erreur WebSocket', 'error');
        };
    }
    
    handleWebSocketMessage(message) {
        switch (message.type) {
            case 'status':
            case 'pong':
                this.updateStatus(message.data);
                // Hide loading modal if we get a DRIVING or READY status
                if (message.data.status === 'DRIVING' || message.data.status === 'READY') {
                    this.hideLoadingModal();
                }
                // If we get an IDLE status after a reset, refresh the UI
                if (message.data.status === 'IDLE') {
                    this.resetUI();
                    this.hideLoadingModal();
                }
                break;
                
            case 'instruction':
                this.handleNewInstruction(message.data);
                // Hide loading modal when we get our first instruction
                this.hideLoadingModal();
                break;
                
            case 'log':
                this.addLog(message.message);
                break;
                
            default:
                console.log('Unknown message type:', message.type);
        }
    }
    
    handleNewInstruction(instruction) {
        console.log('📍 New instruction received:', instruction);

        // Mettre à jour la position si on a des coordonnées
        if (instruction.latitude && instruction.longitude) {
            const newPosition = [instruction.latitude, instruction.longitude];
            this.updateCarPosition(newPosition);
        }

        // Mettre à jour l'instruction courante
        this.updateCurrentInstruction(instruction);

        // Ajouter au log
        this.addLog(`📍 ${instruction.action}: ${instruction.target}`, 'info');
    }
    
    updateCarPosition(newPosition) {
        console.log('🚗 Updating car position to:', newPosition);
        
        // Animer le déplacement du marqueur
        this.carMarker.setLatLng(newPosition);
        
        // Ajouter le point au trajet
        this.routePoints.push(newPosition);
        this.routePolyline.setLatLngs(this.routePoints);
        
        // Centrer la carte sur la nouvelle position
        this.map.setView(newPosition, this.map.getZoom());
        
        // Animation du marqueur
        this.carMarker.getElement()?.classList.add('marker-bounce');
        setTimeout(() => {
            this.carMarker.getElement()?.classList.remove('marker-bounce');
        }, 1000);
        
        this.currentPosition = newPosition;
    }
    
    updateStatus(data) {
        // Mettre à jour le badge de statut
        this.statusBadge.textContent = data.status;
        this.statusBadge.className = `badge status-${data.status.toLowerCase()}`;
        
        // Mettre à jour les statistiques
        this.totalKm.textContent = `${data.total_km_travelled.toFixed(2)} km`;
        this.instructionCount.textContent = `${data.instructions_processed}/${data.total_instructions}`;
        
        // Mettre à jour les boutons selon le statut
        this.updateButtons(data.status);
    }
    
    updateButtons(status) {
        switch (status) {
            case 'IDLE':
                this.btnStartRace.disabled = false;
                this.btnStop.disabled = true;
                this.btnReset.disabled = false;
                break;
                
            case 'READY':
            case 'DRIVING':
                this.btnStartRace.disabled = true;
                this.btnStop.disabled = false;
                this.btnReset.disabled = true;
                break;
                
            case 'COMPLETED':
                this.btnStartRace.disabled = true;
                this.btnStop.disabled = true;
                this.btnReset.disabled = false;
                break;
        }
    }
    
    updateCurrentInstruction(instruction) {
        const actionIcons = {
            'start': '🏁',
            'go_forward': '⬆️',
            'turn_left': '⬅️',
            'turn_right': '➡️',
            'arrival': '🎯'
        };
        
        const icon = actionIcons[instruction.action] || '📍';
        
        this.currentInstructionContent.innerHTML = `
            <div class="instruction-card completed p-3">
                <div class="d-flex align-items-center">
                    <span class="me-2" style="font-size: 1.5rem;">${icon}</span>
                    <div>
                        <strong>${instruction.action.replace('_', ' ').toUpperCase()}</strong><br>
                        <small class="text-muted">${instruction.target}</small><br>
                        <small class="text-success">+${instruction.km_gain} km</small>
                    </div>
                </div>
            </div>
        `;
    }
    
    updateConnectionStatus(status) {
        const statusElement = document.querySelector('.ws-status') || this.createStatusElement();
        
        statusElement.className = `ws-status ws-${status}`;
        
        switch (status) {
            case 'connected':
                statusElement.textContent = '🟢 Connecté';
                break;
            case 'connecting':
                statusElement.textContent = '🟡 Connexion...';
                break;
            case 'disconnected':
                statusElement.textContent = '🔴 Déconnecté';
                break;
        }
    }
    
    createStatusElement() {
        const element = document.createElement('div');
        element.className = 'ws-status';
        document.body.appendChild(element);
        return element;
    }
    
    addLog(message, type = 'info') {
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-${type}`;
        logEntry.textContent = `[${timestamp}] ${message}`;
        
        this.logsContainer.appendChild(logEntry);
        
        // Limiter le nombre de logs affichés
        while (this.logsContainer.children.length > 100) {
            this.logsContainer.removeChild(this.logsContainer.firstChild);
        }
        
        // Auto-scroll
        this.logsContainer.scrollTop = this.logsContainer.scrollHeight;
    }
    
    showLoadingModal(message) {
        document.getElementById('loading-message').textContent = message;
        this.loadingModal.show();
    }
    
    hideLoadingModal() {
        this.loadingModal.hide();
    }
    
    // API Calls
    async startRace() {
        try {
            this.showLoadingModal('Démarrage de la course...');

            // Timeout côté client aussi pour éviter les blocages
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 20000); // 20 secondes

            const response = await fetch('/api/start-race', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                signal: controller.signal
            });

            clearTimeout(timeoutId);
            const result = await response.json();

            if (result.success) {
                this.addLog('🚀 Course démarrée avec succès!', 'success');
            } else {
                this.addLog(`❌ Échec du démarrage: ${result.message}`, 'error');
            }

            this.hideLoadingModal();
        } catch (error) {
            this.hideLoadingModal();

            if (error.name === 'AbortError') {
                this.addLog('⏰ Timeout lors du démarrage de la course', 'error');
                this.addLog('💡 Vérifiez la connectivité Kafka ou utilisez le mode simulation', 'warning');
            } else {
                console.error('Error starting race:', error);
                this.addLog('❌ Erreur lors du démarrage', 'error');
            }
        }
    }
    
    async stopService() {
        try {
            const response = await fetch('/api/stop', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const result = await response.json();
            this.addLog(result.message, result.success ? 'success' : 'error');
        } catch (error) {
            console.error('Error stopping service:', error);
            this.addLog('❌ Erreur lors de l\'arrêt', 'error');
        }
    }
    
    async resetService() {
        try {
            this.showLoadingModal('Remise à zéro...');

            const response = await fetch('/api/reset', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const result = await response.json();

            if (result.success) {
                // Reset de l'interface
                this.resetUI();
                this.addLog('🔄 Service remis à zéro', 'success');
            } else {
                this.addLog('❌ Échec de la remise à zéro', 'error');
            }

            this.hideLoadingModal();
        } catch (error) {
            console.error('Error resetting service:', error);
            this.addLog('❌ Erreur lors de la remise à zéro', 'error');
            this.hideLoadingModal();
        }
    }
    
    async testConnectivity() {
        try {
            this.connectivityStatus.innerHTML = '<span class="connectivity-testing">🔍 Test en cours...</span>';

            const response = await fetch('/api/test-connectivity');
            const result = await response.json();

            if (result.success) {
                this.connectivityStatus.innerHTML = '<span class="connectivity-success">✅ Connectivité OK</span>';
            } else {
                this.connectivityStatus.innerHTML = '<span class="connectivity-error">❌ Échec de connectivité</span>';
            }

            this.addLog(result.message, result.success ? 'success' : 'error');
        } catch (error) {
            console.error('Error testing connectivity:', error);
            this.connectivityStatus.innerHTML = '<span class="connectivity-error">❌ Erreur de test</span>';
            this.addLog('❌ Erreur lors du test', 'error');
        }
    }
    
    resetUI() {
        console.log('🔄 Resetting UI state...');
        
        // Remettre la position initiale
        this.currentPosition = [45.1885, 5.7245];
        this.carMarker.setLatLng(this.currentPosition);
        this.map.setView(this.currentPosition, 13);
        
        // Vider le trajet
        this.routePoints = [];
        this.routePolyline.setLatLngs([]);
        
        // Reset instruction courante
        this.currentInstructionContent.innerHTML = '<div class="alert alert-info">En attente du démarrage...</div>';
        
        // Reset stats
        this.totalKm.textContent = '0.00 km';
        this.instructionCount.textContent = '0/0';
        
        // Reset connectivité
        this.connectivityStatus.innerHTML = '';
    }
    
    // Heartbeat pour maintenir la connexion
    startHeartbeat() {
        setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000); // Ping toutes les 30 secondes
    }
}

// Initialiser l'application quand le DOM est prêt
document.addEventListener('DOMContentLoaded', () => {
    console.log('🌟 DOM loaded, starting Backend Pilot App...');
    const app = new BackendPilotApp();
    
    // Démarrer le heartbeat
    app.startHeartbeat();
    
    // Exposer l'app globalement pour debug
    window.pilotApp = app;
});