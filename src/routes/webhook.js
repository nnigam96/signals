const express = require('express');
const router = express.Router();
const { getEmail, sendReport } = require('../services/resend');
const { parseEmailPayload } = require('../utils/email');
const { extractIdea, analyzeMarket, generateReport } = require('../services/ai');

/**
 * Run the research pipeline asynchronously
 * @param {Object} parsedEmail - Parsed email data
 */
async function runResearchPipeline(parsedEmail) {
  try {
    console.log(`[Pipeline] Starting research for: ${parsedEmail.from}`);

    // 1. Extract idea from email body using Claude
    console.log('[Pipeline] Step 1: Extracting idea...');
    const idea = await extractIdea(parsedEmail.body || '', parsedEmail.subject);
    console.log(`[Pipeline] Idea extracted: ${idea.summary}`);

    // 2. Search HN discussions
    console.log('[Pipeline] Step 2: Searching HN discussions...');
    let discussions = [];
    try {
      const { searchHN } = require('../services/hn');
      const keywords = idea.keywords?.join(' ') || idea.summary;
      discussions = await searchHN(keywords, '1m');
      console.log(`[Pipeline] Found ${discussions.length} HN discussions`);
    } catch (err) {
      console.error('[Pipeline] HN search failed:', err.message);
    }

    // 3. Compile research data
    const research = {
      papers: [], // Academic paper search not yet implemented
      discussions,
      competitors: [] // Competitor search not yet implemented
    };

    // 4. Analyze market using Claude
    console.log('[Pipeline] Step 3: Analyzing market...');
    const analysis = await analyzeMarket(research, idea.summary);
    console.log(`[Pipeline] Verdict: ${analysis.verdict} (${analysis.confidence}% confidence)`);

    // 5. Generate report
    console.log('[Pipeline] Step 4: Generating report...');
    const report = await generateReport(idea, research, analysis);

    // 6. Send report back to sender
    console.log('[Pipeline] Step 5: Sending report...');
    await sendReport(parsedEmail.from, report, idea.summary);
    console.log(`[Pipeline] Report sent to ${parsedEmail.from}`);

    return report;
  } catch (error) {
    console.error('[Pipeline] Error:', error);
    throw error;
  }
}

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

    // Trigger research pipeline asynchronously (don't wait for completion)
    runResearchPipeline(parsedEmail).catch(err => {
      console.error('Research pipeline failed:', err);
    });

    // Acknowledge webhook receipt immediately
    res.status(200).json({
      success: true,
      message: 'Email received and research pipeline started',
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
