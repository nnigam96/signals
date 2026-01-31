/**
 * Email templates for Signals notifications
 */

const baseStyles = `
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.6;
    color: #1f2937;
    max-width: 600px;
    margin: 0 auto;
    padding: 20px;
    background-color: #f9fafb;
  }
  .container {
    background-color: #ffffff;
    border-radius: 12px;
    padding: 32px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }
  .logo {
    font-size: 24px;
    font-weight: bold;
    color: #2563eb;
    margin-bottom: 24px;
  }
  .button {
    display: inline-block;
    background-color: #2563eb;
    color: white !important;
    padding: 12px 24px;
    border-radius: 6px;
    text-decoration: none;
    font-weight: 600;
    margin: 16px 0;
  }
  .button:hover {
    background-color: #1d4ed8;
  }
  .footer {
    margin-top: 32px;
    padding-top: 16px;
    border-top: 1px solid #e5e7eb;
    font-size: 12px;
    color: #9ca3af;
    text-align: center;
  }
  .progress-bar {
    background-color: #e5e7eb;
    border-radius: 9999px;
    height: 8px;
    overflow: hidden;
    margin: 16px 0;
  }
  .progress-fill {
    background-color: #2563eb;
    height: 100%;
    border-radius: 9999px;
    transition: width 0.3s ease;
  }
  .stage-item {
    padding: 8px 0;
    display: flex;
    align-items: center;
  }
  .stage-icon {
    width: 24px;
    height: 24px;
    margin-right: 12px;
  }
  .stage-complete {
    color: #10b981;
  }
  .stage-current {
    color: #2563eb;
    font-weight: 600;
  }
  .stage-pending {
    color: #9ca3af;
  }
  .data-preview {
    background-color: #f9fafb;
    border-radius: 6px;
    padding: 12px;
    margin: 12px 0;
    font-size: 14px;
  }
  .verdict-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 9999px;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
  }
  .verdict-validated { background-color: #d1fae5; color: #065f46; }
  .verdict-research { background-color: #fef3c7; color: #92400e; }
  .verdict-crowded { background-color: #fee2e2; color: #991b1b; }
`;

/**
 * Sign-up confirmation email template
 */
function signupConfirmation({ email, dashboardId }) {
  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Welcome to Signals</title>
  <style>${baseStyles}</style>
</head>
<body>
  <div class="container">
    <div class="logo">Signals</div>

    <h1 style="font-size: 24px; margin-bottom: 16px;">Welcome! Your dashboard is being prepared.</h1>

    <p>Thanks for signing up. We're currently analyzing your request and gathering market intelligence.</p>

    <p>You'll receive email updates as we:</p>
    <ul>
      <li>Search academic research</li>
      <li>Analyze community discussions</li>
      <li>Identify competitors</li>
      <li>Gather market signals</li>
      <li>Generate your comprehensive report</li>
    </ul>

    <p style="background-color: #eff6ff; padding: 16px; border-radius: 8px; border-left: 4px solid #2563eb;">
      <strong>Dashboard ID:</strong> ${dashboardId}<br>
      <small>Save this ID to check your dashboard status anytime.</small>
    </p>

    <p>We'll notify you the moment your dashboard is ready. This usually takes less than 60 seconds.</p>

    <div class="footer">
      <p>Signals - AI-Powered Market Intelligence</p>
      <p>You're receiving this because you signed up at ${email}</p>
    </div>
  </div>
</body>
</html>
  `.trim();
}

/**
 * Dashboard ready notification template
 */
function dashboardReady({ dashboardId, dashboardUrl, ideaSummary, verdict }) {
  const verdictConfig = {
    'VALIDATED': { class: 'verdict-validated', text: 'Validated', emoji: String.fromCodePoint(0x2705) },
    'NEEDS_RESEARCH': { class: 'verdict-research', text: 'Needs Research', emoji: String.fromCodePoint(0x1F50D) },
    'CROWDED': { class: 'verdict-crowded', text: 'Crowded Market', emoji: String.fromCodePoint(0x26A0, 0xFE0F) }
  };

  const v = verdictConfig[verdict] || verdictConfig['NEEDS_RESEARCH'];

  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Your Dashboard is Ready</title>
  <style>${baseStyles}</style>
</head>
<body>
  <div class="container">
    <div class="logo">Signals</div>

    <h1 style="font-size: 24px; margin-bottom: 16px;">${v.emoji} Your dashboard is ready!</h1>

    <p><strong>Idea analyzed:</strong> ${ideaSummary}</p>

    <p>
      <span class="verdict-badge ${v.class}">${v.text}</span>
    </p>

    <p>We've compiled comprehensive market intelligence including:</p>
    <ul>
      <li>Academic research and citations</li>
      <li>Community discussions from Hacker News</li>
      <li>Competitive landscape analysis</li>
      <li>Market signals and trends</li>
      <li>AI-powered recommendations</li>
    </ul>

    <a href="${dashboardUrl}" class="button">View Your Dashboard</a>

    <p style="font-size: 14px; color: #6b7280;">
      Or copy this link: ${dashboardUrl}
    </p>

    <div class="footer">
      <p>Dashboard ID: ${dashboardId}</p>
      <p>Signals - AI-Powered Market Intelligence</p>
    </div>
  </div>
</body>
</html>
  `.trim();
}

/**
 * Progress update email template
 */
function progressUpdate({ dashboardId, stage, stageDescription, progress, data }) {
  const stages = [
    { id: 'parsing_input', label: 'Analyzing input' },
    { id: 'searching_papers', label: 'Academic research' },
    { id: 'searching_discussions', label: 'Community discussions' },
    { id: 'finding_competitors', label: 'Competitor analysis' },
    { id: 'analyzing_market', label: 'Market signals' },
    { id: 'generating_report', label: 'Generating report' }
  ];

  const currentIndex = stages.findIndex(s => s.id === stage);

  const stageList = stages.map((s, i) => {
    let statusClass = 'stage-pending';
    let icon = String.fromCodePoint(0x25CB); // empty circle

    if (i < currentIndex) {
      statusClass = 'stage-complete';
      icon = String.fromCodePoint(0x2714); // checkmark
    } else if (i === currentIndex) {
      statusClass = 'stage-current';
      icon = String.fromCodePoint(0x25CF); // filled circle
    }

    return `<div class="stage-item ${statusClass}">${icon} ${s.label}</div>`;
  }).join('');

  let dataPreview = '';
  if (data) {
    if (data.papers && data.papers.length > 0) {
      dataPreview = `
        <div class="data-preview">
          <strong>Found ${data.papers.length} relevant papers:</strong>
          <ul>${data.papers.slice(0, 2).map(p => `<li>${p.title}</li>`).join('')}</ul>
        </div>
      `;
    } else if (data.discussions && data.discussions.length > 0) {
      dataPreview = `
        <div class="data-preview">
          <strong>Found ${data.discussions.length} discussions:</strong>
          <ul>${data.discussions.slice(0, 2).map(d => `<li>${d.title}</li>`).join('')}</ul>
        </div>
      `;
    } else if (data.competitors && data.competitors.length > 0) {
      dataPreview = `
        <div class="data-preview">
          <strong>Found ${data.competitors.length} competitors:</strong>
          <ul>${data.competitors.slice(0, 3).map(c => `<li>${c.name}</li>`).join('')}</ul>
        </div>
      `;
    }
  }

  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dashboard Update</title>
  <style>${baseStyles}</style>
</head>
<body>
  <div class="container">
    <div class="logo">Signals</div>

    <h1 style="font-size: 20px; margin-bottom: 8px;">${stageDescription}</h1>

    <div class="progress-bar">
      <div class="progress-fill" style="width: ${progress}%;"></div>
    </div>
    <p style="text-align: center; font-size: 14px; color: #6b7280;">${progress}% complete</p>

    <div style="margin: 24px 0;">
      ${stageList}
    </div>

    ${dataPreview}

    <p style="font-size: 14px; color: #6b7280;">
      We'll email you again when your dashboard is ready, or when we find something interesting.
    </p>

    <div class="footer">
      <p>Dashboard ID: ${dashboardId}</p>
      <p>Signals - AI-Powered Market Intelligence</p>
    </div>
  </div>
</body>
</html>
  `.trim();
}

module.exports = {
  signupConfirmation,
  dashboardReady,
  progressUpdate
};
