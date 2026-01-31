/**
 * Parse webhook payload from Resend
 * @param {Object} email - Full email object from Resend API
 * @returns {Object} - Parsed email data
 */
function parseEmailPayload(email) {
  return {
    id: email.id,
    from: email.from,
    to: email.to,
    subject: email.subject,
    body: email.text || email.html || '',
    html: email.html,
    createdAt: email.created_at
  };
}

/**
 * Format a research report as HTML email
 * @param {Object} report - The report object with sections
 * @returns {string} - Formatted HTML email content
 */
function formatReportEmail(report) {
  const verdictColors = {
    'VALIDATED': { bg: '#10b981', text: 'VALIDATED', emoji: String.fromCodePoint(0x2705) },
    'NEEDS_RESEARCH': { bg: '#f59e0b', text: 'NEEDS MORE RESEARCH', emoji: String.fromCodePoint(0x1F50D) },
    'CROWDED': { bg: '#ef4444', text: 'CROWDED MARKET', emoji: String.fromCodePoint(0x26A0, 0xFE0F) }
  };

  const verdict = verdictColors[report.verdict] || verdictColors['NEEDS_RESEARCH'];

  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Signals Market Intelligence Report</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.6;
      color: #1f2937;
      max-width: 680px;
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
    .verdict-banner {
      background-color: ${verdict.bg};
      color: white;
      padding: 16px 24px;
      border-radius: 8px;
      text-align: center;
      font-size: 18px;
      font-weight: bold;
      margin-bottom: 24px;
    }
    .section {
      margin-bottom: 28px;
    }
    .section-title {
      font-size: 16px;
      font-weight: 600;
      color: #374151;
      border-bottom: 2px solid #e5e7eb;
      padding-bottom: 8px;
      margin-bottom: 16px;
    }
    .section-content {
      color: #4b5563;
    }
    ul {
      padding-left: 20px;
      margin: 0;
    }
    li {
      margin-bottom: 8px;
    }
    a {
      color: #2563eb;
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
    .source {
      font-size: 12px;
      color: #6b7280;
    }
    .footer {
      margin-top: 32px;
      padding-top: 16px;
      border-top: 1px solid #e5e7eb;
      font-size: 12px;
      color: #9ca3af;
      text-align: center;
    }
    .competitor-card {
      background-color: #f9fafb;
      border-radius: 6px;
      padding: 12px;
      margin-bottom: 8px;
    }
    .competitor-name {
      font-weight: 600;
      color: #1f2937;
    }
    .paper-citation {
      font-size: 12px;
      color: #6b7280;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="verdict-banner">
      ${verdict.emoji} ${verdict.text}
    </div>

    ${report.executiveSummary ? `
    <div class="section">
      <h2 class="section-title">Executive Summary</h2>
      <div class="section-content">
        <p>${report.executiveSummary}</p>
      </div>
    </div>
    ` : ''}

    ${report.academicResearch && report.academicResearch.length > 0 ? `
    <div class="section">
      <h2 class="section-title">Academic Research</h2>
      <div class="section-content">
        <ul>
          ${report.academicResearch.map(paper => `
            <li>
              <a href="${paper.url}" target="_blank">${paper.title}</a>
              <span class="paper-citation">(${paper.year}, ${paper.citationCount} citations)</span>
              ${paper.summary ? `<p>${paper.summary}</p>` : ''}
            </li>
          `).join('')}
        </ul>
      </div>
    </div>
    ` : ''}

    ${report.communityDiscussion && report.communityDiscussion.length > 0 ? `
    <div class="section">
      <h2 class="section-title">Community Discussion</h2>
      <div class="section-content">
        <ul>
          ${report.communityDiscussion.map(thread => `
            <li>
              <a href="${thread.url}" target="_blank">${thread.title}</a>
              <span class="source">(${thread.points} points, ${thread.numComments} comments)</span>
            </li>
          `).join('')}
        </ul>
      </div>
    </div>
    ` : ''}

    ${report.competitiveLandscape && report.competitiveLandscape.length > 0 ? `
    <div class="section">
      <h2 class="section-title">Competitive Landscape</h2>
      <div class="section-content">
        ${report.competitiveLandscape.map(comp => `
          <div class="competitor-card">
            <div class="competitor-name">
              <a href="${comp.url}" target="_blank">${comp.name}</a>
            </div>
            <p>${comp.description || comp.snippet || ''}</p>
          </div>
        `).join('')}
      </div>
    </div>
    ` : ''}

    ${report.marketSignals && report.marketSignals.length > 0 ? `
    <div class="section">
      <h2 class="section-title">Market Signals</h2>
      <div class="section-content">
        <ul>
          ${report.marketSignals.map(signal => `
            <li>
              <strong>${signal.company}:</strong> ${signal.description}
              <span class="source">(${signal.signalType})</span>
            </li>
          `).join('')}
        </ul>
      </div>
    </div>
    ` : ''}

    ${report.recommendations ? `
    <div class="section">
      <h2 class="section-title">Recommendations</h2>
      <div class="section-content">
        ${Array.isArray(report.recommendations)
          ? `<ul>${report.recommendations.map(rec => `<li>${rec}</li>`).join('')}</ul>`
          : `<p>${report.recommendations}</p>`
        }
      </div>
    </div>
    ` : ''}

    <div class="footer">
      <p>Generated by Signals - AI-Powered Market Intelligence</p>
      <p>Report generated at ${new Date().toISOString()}</p>
    </div>
  </div>
</body>
</html>
  `.trim();
}

/**
 * Extract plain text from HTML content
 * @param {string} html - HTML content
 * @returns {string} - Plain text content
 */
function htmlToText(html) {
  if (!html) return '';
  return html
    .replace(/<[^>]*>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

module.exports = {
  parseEmailPayload,
  formatReportEmail,
  htmlToText
};
