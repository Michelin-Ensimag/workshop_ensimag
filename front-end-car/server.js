const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');
const app = express();
const port = 3001;

// Middleware to parse POST data
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.static('public'));

// Route to handle the action API
app.post('/api/action',async (req, res) => {
  const { action, instruction } = req.body;
  console.log(`Received action: ${action}`); // Log action received

  try {
    console.log("Checkpoint for", instruction )
    await axios.post('http://localhost:8000/checkpoint',{
        "type": "checkpoint", 
        "step": instruction.step,
        "id": instruction.step,
        "group_id": "tkfegbl1.testgroup",
        "km_travelled": 265.5
      }, { headers: {
        'Content-Type': 'application/json',
    }});

  } catch (error) {
    console.error('Error sending checkpoint to validate instruction', error);
    res.status(500).send('Error validating instruction');
  }

  try {
    const response = await axios.get('http://localhost:8000/next-instruction');
    console.log('Received instruction from external service:', response.data); // Log instruction received
    // Check if the response data is null
    if (response.data === null) {
      return res.send({ action: "finish" }); // Return the finish action if response is null
    }

    res.send(response.data); // Return the response of the API
   } catch (error) {
    console.error('Error calling /instruction endpoint:', error); // Log l'erreur
    res.status(500).send('Error readying simulation');
  }

});

// Endpoint /start
app.get('/api/instruction', async (req, res) => {
  console.log('Received request for instruction'); // Log when the endpoint is hit
  try {
    // Effectuer une requête POST à localhost:8000/ready avec un corps vide
    const response = await axios.get('http://localhost:8000/next-instruction');
    console.log('Received instruction from external service:', response.data); // Log instruction received
    res.send(response.data); // Renvoie la réponse de l'API
  } catch (error) {
    console.error('Error calling /instruction endpoint:', error); // Log l'erreur
    res.status(500).send('Error readying simulation');
  }
});

// Endpoint /ready
app.post('/api/ready', async (req, res) => {
  console.log('Received request to start the simulation'); // Log quand l'endpoint est atteint
  try {
    // Effectuer une requête POST à localhost:8000/ready avec un corps vide
    const response = await axios.post('http://localhost:8000/ready', {});
    console.log('Successfully ready for simulation:', response.data); // Log réponse de l'API
    res.send(response.data); // Renvoie la réponse de l'API
  } catch (error) {
    console.error('Error calling /ready endpoint:', error); // Log l'erreur
    res.status(500).send('Error readying simulation');
  }
});

app.get('/favicon.ico', (req, res) => {
  res.sendFile(__dirname + '/public/favicon.svg');
});

// Start the server
app.listen(port, () => {
  console.log(`Server is running on http://localhost:${port}`); // Log le démarrage du serveur
});
