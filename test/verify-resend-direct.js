/**
 * Direct Resend API Test
 *
 * Tests the Resend email service directly to verify the integration.
 * Run with: node test/verify-resend-direct.js
 */

require('dotenv').config();

const { Resend } = require('resend');

async function testResendDirect() {
  console.log('\n========================================');
  console.log('Direct Resend API Test');
  console.log('========================================\n');

  const apiKey = process.env.RESEND_API_KEY;
  console.log(`API Key configured: ${apiKey ? 'Yes (' + apiKey.substring(0, 10) + '...)' : 'No'}`);
  console.log(`From Email: ${process.env.RESEND_FROM_EMAIL || 'Not set'}`);

  if (!apiKey || apiKey === 're_test_placeholder' || apiKey === 're_your_api_key_here') {
    console.log('\n⚠️  No valid Resend API key found.');
    console.log('To test actual email delivery:');
    console.log('  1. Sign up at https://resend.com');
    console.log('  2. Get your API key from https://resend.com/api-keys');
    console.log('  3. Update .env with: RESEND_API_KEY=re_xxxxx');
    console.log('\nSkipping direct API test.\n');

    // Test that the service module loads correctly
    console.log('Testing service module loads...');
    const { sendEmail, getEmail, sendReport } = require('../src/services/resend');
    console.log('✓ resend.js service module loaded');

    const { sendSignupConfirmation, sendDashboardReady, sendProgressUpdate } = require('../src/services/notifications');
    console.log('✓ notifications.js service module loaded');

    const templates = require('../src/utils/emailTemplates');
    console.log('✓ emailTemplates.js module loaded');

    // Test template rendering
    console.log('\nTesting template rendering...');
    const signupHtml = templates.signupConfirmation({
      email: 'test@example.com',
      dashboardId: 'test-123'
    });
    console.log(`✓ signupConfirmation template renders (${signupHtml.length} chars)`);

    const readyHtml = templates.dashboardReady({
      dashboardId: 'test-123',
      dashboardUrl: 'https://example.com/dashboard/test-123',
      ideaSummary: 'AI Market Intelligence',
      verdict: 'VALIDATED'
    });
    console.log(`✓ dashboardReady template renders (${readyHtml.length} chars)`);

    const progressHtml = templates.progressUpdate({
      dashboardId: 'test-123',
      stage: 'searching_papers',
      stageDescription: 'Searching academic research...',
      progress: 30,
      data: { papers: [{ title: 'Test Paper' }] }
    });
    console.log(`✓ progressUpdate template renders (${progressHtml.length} chars)`);

    console.log('\n========================================');
    console.log('Service Integration Test: PASSED');
    console.log('(Email delivery not tested - no API key)');
    console.log('========================================\n');
    return;
  }

  const resend = new Resend(apiKey);

  // Test 1: Send a simple test email
  console.log('\nTest 1: Sending test email...');
  try {
    const testEmail = process.env.TEST_EMAIL || 'delivered@resend.dev';
    const result = await resend.emails.send({
      from: process.env.RESEND_FROM_EMAIL || 'Signals <onboarding@resend.dev>',
      to: [testEmail],
      subject: 'Signals Resend Integration Test',
      html: `
        <h1>Resend Integration Test</h1>
        <p>This email confirms that the Resend integration is working correctly.</p>
        <p><strong>Timestamp:</strong> ${new Date().toISOString()}</p>
        <p><strong>API Key:</strong> ${apiKey.substring(0, 10)}...</p>
      `
    });

    if (result.data && result.data.id) {
      console.log(`✓ Email sent successfully!`);
      console.log(`  Email ID: ${result.data.id}`);
      console.log(`  Recipient: ${testEmail}`);
    } else if (result.error) {
      console.log(`✗ Email failed: ${result.error.message}`);
    }
  } catch (error) {
    console.log(`✗ Email failed: ${error.message}`);
  }

  // Test 2: Using the service module
  console.log('\nTest 2: Testing via service module...');
  try {
    const { sendEmail } = require('../src/services/resend');
    const testEmail = process.env.TEST_EMAIL || 'delivered@resend.dev';

    const result = await sendEmail({
      to: testEmail,
      subject: 'Signals Service Module Test',
      html: '<h1>Service Module Test</h1><p>If you receive this, the service module is working!</p>'
    });

    if (result && result.id) {
      console.log(`✓ Service module email sent!`);
      console.log(`  Email ID: ${result.id}`);
    } else {
      console.log(`✗ Service module test failed: No email ID returned`);
    }
  } catch (error) {
    console.log(`✗ Service module test failed: ${error.message}`);
  }

  // Test 3: Full notification flow
  console.log('\nTest 3: Testing notification service...');
  try {
    const { sendSignupConfirmation } = require('../src/services/notifications');
    const testEmail = process.env.TEST_EMAIL || 'delivered@resend.dev';

    const result = await sendSignupConfirmation(testEmail, 'test-dashboard-' + Date.now());

    if (result && result.id) {
      console.log(`✓ Signup confirmation email sent!`);
      console.log(`  Email ID: ${result.id}`);
    } else {
      console.log(`✗ Notification test failed: No email ID returned`);
    }
  } catch (error) {
    console.log(`✗ Notification test failed: ${error.message}`);
  }

  console.log('\n========================================');
  console.log('Direct Resend Test Complete');
  console.log('========================================\n');
}

testResendDirect().catch(console.error);
