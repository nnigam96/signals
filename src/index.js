require('dotenv').config();

const express = require('express');
const webhookRoutes = require('./routes/webhook');
const signupRoutes = require('./routes/signup');
const notifyRoutes = require('./routes/notify');

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

// Routes
app.use('/webhook', webhookRoutes);
app.use('/signup', signupRoutes);
app.use('/notify', notifyRoutes);

// Start server
app.listen(PORT, () => {
  console.log(`Signals server running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
  console.log(`Email webhook: http://localhost:${PORT}/webhook/email`);
  console.log(`Signup: http://localhost:${PORT}/signup`);
  console.log(`Notifications: http://localhost:${PORT}/notify`);
});

module.exports = app;
