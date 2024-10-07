var current_data;

// Function to update time or date
function updateDisplay(selector, formatFunc) {
  const currentDate = new Date();
  const formattedString = formatFunc(currentDate);
  document.querySelector(selector).innerHTML = formattedString;
}

// Format time
function formatTime(date) {
  let hours = date.getHours();
  let minutes = date.getMinutes();
  hours = (hours < 10 ? "0" : "") + hours;
  minutes = (minutes < 10 ? "0" : "") + minutes;
  return `${hours} : ${minutes}`;
}

// Format date
function formatDate(date) {
  let day = date.getDate();
  let month = date.getMonth() + 1;
  let year = date.getFullYear();
  month = (month < 10 ? "0" : "") + month;
  return `${day} / ${month} / ${year}`;
}

// Update time and date at intervals
setInterval(() => updateDisplay(".time", formatTime), 1000);
setInterval(() => updateDisplay(".date", formatDate), 1000);

// Update speedometer
const currentSpeedElement = document.getElementById('current-speed');
const speedometerPointer = document.querySelector('.speedometer-pointer');

function updateSpeedometer() {
  const currentSpeed = parseFloat(currentSpeedElement.textContent);
  const maxSpeed = 300; // Max speed in km/h
  const minAngle = 20; // Min angle for 0 km/h
  const maxAngle = 340; // Max angle for 300 km/h
  const angle = ((currentSpeed / maxSpeed) * (maxAngle - minAngle)) + minAngle;
  speedometerPointer.style.transform = `rotate(${angle}deg)`;
}

setInterval(updateSpeedometer, 1000); // Update speedometer every second
updateSpeedometer(); // Initial call

$(document).ready(function () {
  // Show modal on load
  $("#startModal").show();

  // Close modal and start polling
  $("#startModal .close").click(function () {
    $("#startModal").hide();
    startPolling(); // Start polling after closing modal
  });

  // Start button functionality
  $("#startButton").click(function () {
    $.ajax({
      url: '/api/ready', // Replace with your endpoint
      method: 'POST',
      success: function (response) {
        console.log('Simulation started successfully', response);
        $("#startModal").hide();
        startPolling();
      },
      error: function (error) {
        console.error('Error starting simulation', error);
      }
    });
  });

  let pollingInterval;

  function handleAction(data) {
    document.getElementById('action').textContent = data.action.charAt(0).toUpperCase() + data.action.slice(1);
    document.getElementById('content').textContent = data.target;

    if (data.action === 'finish') {
      $("#finishModal").show(); 
      return; 
    }
    
    if (data.action === 'go_forward') {
      document.querySelector('.vehicle-icon').classList.add('signal-selected');
    } else {
      const signalClass = data.action === 'turn_left' ? '.signal-left' : (data.action === 'turn_right' ? '.signal-right' : null);
      if (signalClass) {
        document.querySelector(signalClass).classList.add('signal-selected');
      } else {
        $("#errorModal").show();
        document.querySelector("#errorModal").classList.add('signal-selected');
      }
    }
  }
  
  async function fetchInstruction() {
    try {
      const response = await fetch('/api/instruction');
      const data = await response.json();
      current_data = data;
      handleAction(data);
    } catch (error) {
      console.error('Error fetching instruction:', error);
    }
  }
  
  function startPolling() {
    pollingInterval = setInterval(async () => {
      if (document.querySelector('.signal-selected')) {
        clearInterval(pollingInterval);
        return;
      }
      await fetchInstruction();
    }, 2000);
  }
  
  $(document).on('click', '.signal-selected', async function() {
    $(this).removeClass('signal-selected');
    this.style.color = '';
    const direction = $(this).hasClass('signal-left') ? 'left' : (this.classList.contains('signal-right') ? 'right' : null);
  
    try {
      const response = await fetch('/api/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: direction, instruction: current_data }),
      });
  
      const data = await response.json();
      handleAction(data);
    } catch (error) {
      console.error('Error calling action API:', error);
    }
  });

});
