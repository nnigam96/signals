require('dotenv').config();

const express = require('express');
const webhookRoutes = require('./routes/webhook');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    service: 'signals'
  });
});

// Webhook routes
app.use('/webhook', webhookRoutes);

// Start server
app.listen(PORT, () => {
  console.log(`Signals server running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
  console.log(`Email webhook: http://localhost:${PORT}/webhook/email`);
});

module.exports = app;
