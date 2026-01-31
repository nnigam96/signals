/**
 * End-to-End Test for Resend Email Integration
 *
 * This script tests the complete email flow:
 * 1. Server health check
 * 2. Signup with confirmation email
 * 3. Progress notifications
 * 4. Dashboard ready notification
 * 5. Webhook endpoint verification
 *
 * Usage:
 *   RESEND_API_KEY=re_xxx TEST_EMAIL=your@email.com node test/e2e-resend.test.js
 */

const http = require('http');

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';
const TEST_EMAIL = process.env.TEST_EMAIL || 'test@example.com';

// Test results tracking
const results = {
  passed: 0,
  failed: 0,
  tests: []
};

/**
 * Make HTTP request
 */
function request(method, path, body = null) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, BASE_URL);
    const options = {
      hostname: url.hostname,
      port: url.port,
      path: url.pathname,
      method,
      headers: {
        'Content-Type': 'application/json'
      }
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve({
            status: res.statusCode,
            data: JSON.parse(data)
          });
        } catch {
          resolve({
            status: res.statusCode,
            data: data
          });
        }
      });
    });

    req.on('error', reject);

    if (body) {
      req.write(JSON.stringify(body));
    }

    req.end();
  });
}

/**
 * Test helper
 */
async function test(name, fn) {
  try {
    await fn();
    results.passed++;
    results.tests.push({ name, status: 'PASS' });
    console.log(`✓ ${name}`);
  } catch (error) {
    results.failed++;
    results.tests.push({ name, status: 'FAIL', error: error.message });
    console.log(`✗ ${name}`);
    console.log(`  Error: ${error.message}`);
  }
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

/**
 * Run all tests
 */
async function runTests() {
  console.log('\n========================================');
  console.log('Resend Integration E2E Tests');
  console.log('========================================');
  console.log(`Base URL: ${BASE_URL}`);
  console.log(`Test Email: ${TEST_EMAIL}`);
  console.log('========================================\n');

  let dashboardId = null;

  // Test 1: Health Check
  await test('Server health check', async () => {
    const res = await request('GET', '/health');
    assert(res.status === 200, `Expected status 200, got ${res.status}`);
    assert(res.data.status === 'healthy', `Expected status healthy, got ${res.data.status}`);
  });

  // Test 2: Webhook GET endpoint
  await test('Webhook verification endpoint (GET)', async () => {
    const res = await request('GET', '/webhook/email');
    assert(res.status === 200, `Expected status 200, got ${res.status}`);
    assert(res.data.status === 'ready', `Expected status ready, got ${res.data.status}`);
    assert(res.data.endpoint === '/webhook/email', 'Endpoint mismatch');
  });

  // Test 3: Signup with invalid email
  await test('Signup rejects invalid email', async () => {
    const res = await request('POST', '/signup', {
      email: 'invalid-email'
    });
    assert(res.status === 400, `Expected status 400, got ${res.status}`);
    assert(res.data.error === 'Invalid email format', 'Expected invalid email error');
  });

  // Test 4: Signup without email
  await test('Signup rejects missing email', async () => {
    const res = await request('POST', '/signup', {});
    assert(res.status === 400, `Expected status 400, got ${res.status}`);
    assert(res.data.error === 'Email is required', 'Expected email required error');
  });

  // Test 5: Successful signup (sends confirmation email)
  await test('Signup with valid email sends confirmation', async () => {
    const res = await request('POST', '/signup', {
      email: TEST_EMAIL,
      ideaText: 'AI-powered market intelligence platform'
    });
    assert(res.status === 201, `Expected status 201, got ${res.status}`);
    assert(res.data.success === true, 'Expected success to be true');
    assert(res.data.dashboardId, 'Expected dashboardId in response');
    dashboardId = res.data.dashboardId;
    console.log(`    Dashboard ID: ${dashboardId}`);
  });

  // Test 6: Get signup status
  await test('Get signup status by dashboard ID', async () => {
    const res = await request('GET', `/signup/${dashboardId}`);
    assert(res.status === 200, `Expected status 200, got ${res.status}`);
    assert(res.data.dashboardId === dashboardId, 'Dashboard ID mismatch');
    assert(res.data.status === 'processing', 'Expected status processing');
    assert(res.data.notificationsEnabled === true, 'Expected notifications enabled');
  });

  // Test 7: Get stages
  await test('Get notification stages', async () => {
    const res = await request('GET', '/notify/stages');
    assert(res.status === 200, `Expected status 200, got ${res.status}`);
    assert(Array.isArray(res.data.stages), 'Expected stages array');
    assert(res.data.stages.length === 7, `Expected 7 stages, got ${res.data.stages.length}`);
    console.log(`    Stages: ${res.data.stages.map(s => s.value).join(', ')}`);
  });

  // Test 8: Progress notification - stage 1
  await test('Send progress notification (parsing_input)', async () => {
    const res = await request('POST', '/notify/progress', {
      dashboardId,
      stage: 'parsing_input',
      progress: 10
    });
    assert(res.status === 200, `Expected status 200, got ${res.status}`);
    assert(res.data.success === true, 'Expected success to be true');
    assert(res.data.stage === 'parsing_input', 'Stage mismatch');
  });

  // Test 9: Progress notification - stage 2 with data
  await test('Send progress notification with data (searching_papers)', async () => {
    const res = await request('POST', '/notify/progress', {
      dashboardId,
      stage: 'searching_papers',
      progress: 30,
      data: {
        papers: [
          { title: 'Machine Learning for Market Analysis' },
          { title: 'AI in Business Intelligence' }
        ]
      }
    });
    assert(res.status === 200, `Expected status 200, got ${res.status}`);
    assert(res.data.success === true, 'Expected success to be true');
  });

  // Test 10: Progress notification - invalid stage
  await test('Progress notification rejects invalid stage', async () => {
    const res = await request('POST', '/notify/progress', {
      dashboardId,
      stage: 'invalid_stage',
      progress: 50
    });
    assert(res.status === 400, `Expected status 400, got ${res.status}`);
    assert(res.data.error === 'Invalid stage', 'Expected invalid stage error');
  });

  // Test 11: Progress notification - missing fields
  await test('Progress notification rejects missing fields', async () => {
    const res = await request('POST', '/notify/progress', {
      dashboardId
    });
    assert(res.status === 400, `Expected status 400, got ${res.status}`);
  });

  // Test 12: Progress notification - nonexistent dashboard
  await test('Progress notification fails for nonexistent dashboard', async () => {
    const res = await request('POST', '/notify/progress', {
      dashboardId: 'nonexistent-id',
      stage: 'parsing_input',
      progress: 10
    });
    assert(res.status === 404, `Expected status 404, got ${res.status}`);
  });

  // Test 13: Toggle notifications off
  await test('Toggle notifications off', async () => {
    const res = await request('PATCH', `/signup/${dashboardId}/notifications`, {
      enabled: false
    });
    assert(res.status === 200, `Expected status 200, got ${res.status}`);
    assert(res.data.notificationsEnabled === false, 'Expected notifications disabled');
  });

  // Test 14: Progress notification skipped when disabled
  await test('Progress notification skipped when disabled', async () => {
    const res = await request('POST', '/notify/progress', {
      dashboardId,
      stage: 'finding_competitors',
      progress: 60
    });
    assert(res.status === 200, `Expected status 200, got ${res.status}`);
    assert(res.data.skipped === true, 'Expected notification to be skipped');
  });

  // Test 15: Toggle notifications back on
  await test('Toggle notifications back on', async () => {
    const res = await request('PATCH', `/signup/${dashboardId}/notifications`, {
      enabled: true
    });
    assert(res.status === 200, `Expected status 200, got ${res.status}`);
    assert(res.data.notificationsEnabled === true, 'Expected notifications enabled');
  });

  // Test 16: Dashboard ready notification - missing fields
  await test('Dashboard ready rejects missing fields', async () => {
    const res = await request('POST', '/notify/ready', {
      dashboardId
    });
    assert(res.status === 400, `Expected status 400, got ${res.status}`);
  });

  // Test 17: Dashboard ready notification - success
  await test('Send dashboard ready notification', async () => {
    const res = await request('POST', '/notify/ready', {
      dashboardId,
      dashboardUrl: 'https://signals.dev/dashboard/' + dashboardId,
      ideaSummary: 'AI-powered market intelligence platform',
      verdict: 'VALIDATED'
    });
    assert(res.status === 200, `Expected status 200, got ${res.status}`);
    assert(res.data.success === true, 'Expected success to be true');
  });

  // Test 18: Verify final status
  await test('Verify final dashboard status', async () => {
    const res = await request('GET', `/signup/${dashboardId}`);
    assert(res.status === 200, `Expected status 200, got ${res.status}`);
    assert(res.data.status === 'ready', 'Expected status to be ready');
  });

  // Test 19: Webhook POST with mock payload
  await test('Webhook handles missing email_id', async () => {
    const res = await request('POST', '/webhook/email', {
      type: 'email.received',
      data: {}
    });
    assert(res.status === 400, `Expected status 400, got ${res.status}`);
    assert(res.data.error === 'Missing email_id in payload', 'Expected missing email_id error');
  });

  // Print summary
  console.log('\n========================================');
  console.log('Test Results Summary');
  console.log('========================================');
  console.log(`Total: ${results.passed + results.failed}`);
  console.log(`Passed: ${results.passed}`);
  console.log(`Failed: ${results.failed}`);
  console.log('========================================\n');

  if (results.failed > 0) {
    console.log('Failed tests:');
    results.tests
      .filter(t => t.status === 'FAIL')
      .forEach(t => console.log(`  - ${t.name}: ${t.error}`));
    console.log('');
  }

  // Check if emails were actually sent
  if (process.env.RESEND_API_KEY && process.env.RESEND_API_KEY !== 're_your_api_key_here') {
    console.log('========================================');
    console.log('Email Verification');
    console.log('========================================');
    console.log(`Emails should have been sent to: ${TEST_EMAIL}`);
    console.log('Please check your inbox for:');
    console.log('  1. Signup confirmation email');
    console.log('  2. Progress update emails (parsing_input, searching_papers)');
    console.log('  3. Dashboard ready email with VALIDATED verdict');
    console.log('========================================\n');
  } else {
    console.log('========================================');
    console.log('Note: No valid RESEND_API_KEY found');
    console.log('Email sending tests may have failed.');
    console.log('Set RESEND_API_KEY env var to test actual email delivery.');
    console.log('========================================\n');
  }

  process.exit(results.failed > 0 ? 1 : 0);
}

// Run tests
runTests().catch(err => {
  console.error('Test runner error:', err);
  process.exit(1);
});
