document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('fire-severity-form');
  const resultElem = document.getElementById('prediction-result');
  const errorElem = document.getElementById('prediction-error');
  const placeholderElem = document.getElementById('prediction-placeholder');

  const severityLevelElem = document.getElementById('severity-level');
  const confidenceLevelElem = document.getElementById('confidence-level');
  const severityValueElem = document.getElementById('severity-value');
  const severityBarElem = document.getElementById('severity-bar');
  const modelUsedElem = document.getElementById('model-used');
  const responseTimeElem = document.getElementById('response-time');
  const predictionTimeElem = document.getElementById('prediction-time');

  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    const temperature = parseFloat(document.getElementById('temperature').value);
    const smoke_density = parseFloat(document.getElementById('smoke_density').value);
    const gas_level = parseFloat(document.getElementById('gas_level').value);
    const humidity = parseFloat(document.getElementById('humidity').value);
    const model_type = document.getElementById('model_type').value;

    errorElem.textContent = '';
    errorElem.classList.add('hidden');
    resultElem.classList.add('hidden');
    placeholderElem.classList.remove('hidden');

    try {
      const startTime = performance.now();
      const response = await fetch('http://localhost:8000/predict', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          temperature,
          smoke_density,
          gas_level,
          humidity,
          model_type
        })
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      const data = await response.json();
      const endTime = performance.now();

      // Update UI elements with prediction data
      severityLevelElem.textContent = data.fire_severity_level || 'Unknown';
      confidenceLevelElem.textContent = `Confidence: ${data.confidence ? (data.confidence * 100).toFixed(0) + '%' : 'N/A'}`;
      severityValueElem.textContent = data.severity_value ? data.severity_value.toFixed(2) : 'N/A';
      severityBarElem.style.width = data.severity_value ? `${(data.severity_value * 100).toFixed(0)}%` : '0%';
      modelUsedElem.textContent = data.model_used || 'Unknown';
      responseTimeElem.textContent = `${((endTime - startTime) / 1000).toFixed(2)}s`;
      predictionTimeElem.textContent = new Date().toLocaleTimeString();

      placeholderElem.classList.add('hidden');
      errorElem.classList.add('hidden');
      resultElem.classList.remove('hidden');
    } catch (error) {
      errorElem.textContent = `Error: ${error.message}`;
      errorElem.classList.remove('hidden');
      resultElem.classList.add('hidden');
      placeholderElem.classList.add('hidden');
    }
  });

  // Modularize: Real-time chart update
  window.updateTempChart = function(temp) {
    const tempChartData = window.tempChartData;
    const tempChart = window.tempChart;
    const now = new Date().toLocaleTimeString();
    tempChartData.labels.push(now);
    tempChartData.datasets[0].data.push(temp);
    if (tempChartData.labels.length > 20) {
      tempChartData.labels.shift();
      tempChartData.datasets[0].data.shift();
    }
    tempChart.update();
  }

  // Modularize: Authentication (frontend only)
  window.handleLogin = function() {
    document.getElementById('login-btn').classList.add('hidden');
    document.getElementById('logout-btn').classList.remove('hidden');
    document.getElementById('auth-status').textContent = 'Logged in';
  }
  window.handleLogout = function() {
    document.getElementById('login-btn').classList.remove('hidden');
    document.getElementById('logout-btn').classList.add('hidden');
    document.getElementById('auth-status').textContent = 'Logged out';
  }
});
