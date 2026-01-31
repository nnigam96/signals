const express = require('express');
const router = express.Router();
const {
  sendDashboardReady,
  sendProgressUpdate,
  ProgressStage,
  stageDescriptions
} = require('../services/notifications');
const signupRoutes = require('./signup');

/**
 * Send progress update notification
 * Called by the research pipeline as each stage completes
 *
 * POST /notify/progress
 * Body: { dashboardId: string, stage: string, progress: number, data?: object }
 */
router.post('/progress', async (req, res) => {
  try {
    const { dashboardId, stage, progress, data } = req.body;

    if (!dashboardId || !stage || progress === undefined) {
      return res.status(400).json({
        error: 'Missing required fields: dashboardId, stage, progress'
      });
    }

    // Validate stage
    if (!Object.values(ProgressStage).includes(stage)) {
      return res.status(400).json({
        error: 'Invalid stage',
        validStages: Object.values(ProgressStage)
      });
    }

    // Get signup info
    const signup = signupRoutes.getSignup(dashboardId);

    if (!signup) {
      return res.status(404).json({ error: 'Dashboard not found' });
    }

    if (!signup.notificationsEnabled) {
      return res.json({
        success: true,
        skipped: true,
        message: 'Notifications disabled for this dashboard'
      });
    }

    // Send progress update email
    await sendProgressUpdate(signup.email, {
      dashboardId,
      stage,
      progress,
      data
    });

    // Update signup status
    signupRoutes.updateSignup(dashboardId, {
      status: stage,
      progress,
      lastUpdated: new Date().toISOString()
    });

    console.log(`Progress update sent: ${dashboardId} -> ${stage} (${progress}%)`);

    res.json({
      success: true,
      dashboardId,
      stage,
      progress,
      stageDescription: stageDescriptions[stage]
    });

  } catch (error) {
    console.error('Progress notification error:', error);
    res.status(500).json({
      error: 'Failed to send progress notification',
      message: error.message
    });
  }
});

/**
 * Send dashboard ready notification
 * Called when all research is complete and dashboard is ready
 *
 * POST /notify/ready
 * Body: { dashboardId: string, dashboardUrl: string, ideaSummary: string, verdict: string }
 */
router.post('/ready', async (req, res) => {
  try {
    const { dashboardId, dashboardUrl, ideaSummary, verdict } = req.body;

    if (!dashboardId || !dashboardUrl || !ideaSummary) {
      return res.status(400).json({
        error: 'Missing required fields: dashboardId, dashboardUrl, ideaSummary'
      });
    }

    // Get signup info
    const signup = signupRoutes.getSignup(dashboardId);

    if (!signup) {
      return res.status(404).json({ error: 'Dashboard not found' });
    }

    // Send dashboard ready email
    await sendDashboardReady(signup.email, {
      dashboardId,
      dashboardUrl,
      ideaSummary,
      verdict: verdict || 'NEEDS_RESEARCH'
    });

    // Update signup status
    signupRoutes.updateSignup(dashboardId, {
      status: 'ready',
      progress: 100,
      dashboardUrl,
      verdict,
      completedAt: new Date().toISOString()
    });

    console.log(`Dashboard ready notification sent: ${dashboardId}`);

    res.json({
      success: true,
      dashboardId,
      message: 'Dashboard ready notification sent'
    });

  } catch (error) {
    console.error('Dashboard ready notification error:', error);
    res.status(500).json({
      error: 'Failed to send dashboard ready notification',
      message: error.message
    });
  }
});

/**
 * Get available progress stages
 *
 * GET /notify/stages
 */
router.get('/stages', (req, res) => {
  res.json({
    stages: Object.entries(ProgressStage).map(([key, value]) => ({
      key,
      value,
      description: stageDescriptions[value]
    }))
  });
});

module.exports = router;
