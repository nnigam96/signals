const express = require('express');
const router = express.Router();
const crypto = require('crypto');
const { sendSignupConfirmation } = require('../services/notifications');

// In-memory store for demo (replace with MongoDB in production)
const signups = new Map();

/**
 * Register email for dashboard notifications
 * Called when user signs up while dashboard is loading
 *
 * POST /signup
 * Body: { email: string, ideaText?: string }
 */
router.post('/', async (req, res) => {
  try {
    const { email, ideaText } = req.body;

    if (!email) {
      return res.status(400).json({ error: 'Email is required' });
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return res.status(400).json({ error: 'Invalid email format' });
    }

    // Generate dashboard ID
    const dashboardId = crypto.randomUUID();

    // Store signup (in production, save to MongoDB)
    signups.set(dashboardId, {
      email,
      ideaText,
      dashboardId,
      createdAt: new Date().toISOString(),
      status: 'processing',
      notificationsEnabled: true
    });

    // Send confirmation email
    await sendSignupConfirmation(email, dashboardId);

    console.log(`Signup registered: ${email} -> Dashboard: ${dashboardId}`);

    res.status(201).json({
      success: true,
      dashboardId,
      message: 'Signup confirmed. You will receive email updates as your dashboard is prepared.'
    });

  } catch (error) {
    console.error('Signup error:', error);
    res.status(500).json({
      error: 'Failed to process signup',
      message: error.message
    });
  }
});

/**
 * Get signup status by dashboard ID
 *
 * GET /signup/:dashboardId
 */
router.get('/:dashboardId', (req, res) => {
  const { dashboardId } = req.params;
  const signup = signups.get(dashboardId);

  if (!signup) {
    return res.status(404).json({ error: 'Dashboard not found' });
  }

  res.json({
    dashboardId: signup.dashboardId,
    status: signup.status,
    createdAt: signup.createdAt,
    notificationsEnabled: signup.notificationsEnabled
  });
});

/**
 * Update notification preferences
 *
 * PATCH /signup/:dashboardId/notifications
 * Body: { enabled: boolean }
 */
router.patch('/:dashboardId/notifications', (req, res) => {
  const { dashboardId } = req.params;
  const { enabled } = req.body;
  const signup = signups.get(dashboardId);

  if (!signup) {
    return res.status(404).json({ error: 'Dashboard not found' });
  }

  signup.notificationsEnabled = enabled;
  signups.set(dashboardId, signup);

  res.json({
    dashboardId,
    notificationsEnabled: signup.notificationsEnabled,
    message: enabled ? 'Notifications enabled' : 'Notifications disabled'
  });
});

// Export signup store for use by notification routes
router.getSignup = (dashboardId) => signups.get(dashboardId);
router.updateSignup = (dashboardId, updates) => {
  const signup = signups.get(dashboardId);
  if (signup) {
    signups.set(dashboardId, { ...signup, ...updates });
  }
};

module.exports = router;
