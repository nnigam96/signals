const express = require('express');
const router = express.Router();
const { getEmail } = require('../services/resend');
const { parseEmailPayload } = require('../utils/email');

/**
 * Resend inbound webhook endpoint
 * Receives email notifications and triggers the research pipeline
 *
 * POST /webhook/email
 */
router.post('/email', async (req, res) => {
  try {
    const webhookPayload = req.body;

    console.log('Received email webhook:', JSON.stringify(webhookPayload, null, 2));

    // Extract email ID from webhook payload
    const emailId = webhookPayload.data?.email_id || webhookPayload.email_id;

    if (!emailId) {
      console.error('No email ID in webhook payload');
      return res.status(400).json({ error: 'Missing email_id in payload' });
    }

    // Fetch full email content from Resend API
    const fullEmail = await getEmail(emailId);

    if (!fullEmail) {
      console.error('Could not fetch email content');
      return res.status(404).json({ error: 'Email not found' });
    }

    // Parse email to extract relevant data
    const parsedEmail = parseEmailPayload(fullEmail);

    console.log('Parsed email:', JSON.stringify(parsedEmail, null, 2));

    // TODO: Trigger research pipeline with parsed email
    // 1. Extract idea from email body using Claude
    // 2. Search academic papers
    // 3. Search HN discussions
    // 4. Find competitors
    // 5. Generate report
    // 6. Send report back to sender

    // Acknowledge webhook receipt
    res.status(200).json({
      success: true,
      message: 'Email received and queued for processing',
      emailId,
      from: parsedEmail.from,
      subject: parsedEmail.subject
    });

  } catch (error) {
    console.error('Webhook processing error:', error);
    res.status(500).json({
      error: 'Internal server error',
      message: error.message
    });
  }
});

/**
 * Webhook verification endpoint (for Resend setup)
 * GET /webhook/email
 */
router.get('/email', (req, res) => {
  res.status(200).json({
    status: 'ready',
    endpoint: '/webhook/email',
    method: 'POST',
    description: 'Resend inbound email webhook endpoint'
  });
});

module.exports = router;
