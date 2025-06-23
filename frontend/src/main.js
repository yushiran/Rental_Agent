import Phaser from 'phaser';
import MainScene from './scenes/MainScene';
import UIScene from './scenes/UIScene';

// Game configuration
const config = {
  type: Phaser.AUTO,
  width: 800,
  height: 600,
  parent: 'game',
  pixelArt: true,
  physics: {
    default: 'arcade',
    arcade: {
      gravity: { y: 0 },
      debug: false
    }
  },
  scene: [MainScene, UIScene]
};

// Initialize the game
window.addEventListener('load', () => {
  window.phaserGame = new Phaser.Game(config);

  // Check backend connection
  checkBackendStatus();

  // Set up UI event listeners
  document.getElementById('initialize-btn').addEventListener('click', initializeSystem);
  document.getElementById('start-btn').addEventListener('click', startNegotiation);
  document.getElementById('reset-btn').addEventListener('click', resetMemory);
});

async function checkBackendStatus() {
  const statusElement = document.getElementById('status');
  try {
    const response = await fetch('http://localhost:8000/');
    if (response.ok) {
      statusElement.textContent = 'Backend Status: Connected';
      statusElement.style.color = '#4CAF50';
      document.getElementById('start-btn').disabled = false;
    } else {
      throw new Error('Backend responded with an error');
    }
  } catch (error) {
    statusElement.textContent = 'Backend Status: Disconnected';
    statusElement.style.color = '#f44336';
    document.getElementById('start-btn').disabled = true;
    
    // Try again in 5 seconds
    setTimeout(checkBackendStatus, 5000);
  }
}

async function initializeSystem() {
  try {
    document.getElementById('initialize-btn').disabled = true;
    const tenantCount = document.getElementById('tenant-count').value || 3;
    
    const response = await fetch('http://localhost:8000/initialize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        tenant_count: parseInt(tenantCount),
        reset_data: false 
      })
    });
    
    if (response.ok) {
      const result = await response.json();
      console.log('System initialized:', result);
      
      // Enable start negotiation button
      document.getElementById('start-btn').disabled = false;
      
      // Pass data to game
      if (window.phaserGame) {
        window.phaserGame.events.emit('system-initialized', result);
      }
      
      // Update status
      document.getElementById('system-status').textContent = 
        `System ready: ${result.data.tenants_count} tenants, ${result.data.properties_count} properties`;
    } else {
      throw new Error('Failed to initialize system');
    }
  } catch (error) {
    console.error('Error initializing system:', error);
    document.getElementById('initialize-btn').disabled = false;
    alert('Failed to initialize system. Check console for details.');
  }
}

async function startNegotiation() {
  try {
    document.getElementById('start-btn').disabled = true;
    
    const response = await fetch('http://localhost:8000/start-negotiation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tenant_ids: [] }) // Use all available tenants
    });
    
    if (response.ok) {
      const result = await response.json();
      console.log('Negotiation started:', result);
      // Store game instance properly
      if (window.phaserGame) {
        window.phaserGame.events.emit('negotiation-started', result);
      }
    } else {
      throw new Error('Failed to start negotiation');
    }
  } catch (error) {
    console.error('Error starting negotiation:', error);
    document.getElementById('start-btn').disabled = false;
    alert('Failed to start negotiation. Check console for details.');
  }
}

async function resetMemory() {
  try {
    document.getElementById('reset-btn').disabled = true;
    const response = await fetch('http://localhost:8000/reset-memory', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    
    if (response.ok) {
      console.log('Memory reset successful');
      document.getElementById('start-btn').disabled = false;
      document.getElementById('reset-btn').disabled = false;
      if (window.phaserGame) {
        window.phaserGame.events.emit('memory-reset');
      }
    } else {
      throw new Error('Failed to reset memory');
    }
  } catch (error) {
    console.error('Error resetting memory:', error);
    document.getElementById('reset-btn').disabled = false;
    alert('Failed to reset memory. Check console for details.');
  }
}
