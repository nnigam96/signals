const { Resend } = require('resend');

const resend = new Resend(process.env.RESEND_API_KEY);

/**
 * Fetch full email content from Resend API
 * Webhook only sends metadata, so we need to fetch the full body
 * @param {string} emailId - The email ID from the webhook payload
 * @returns {Promise<Object>} - Full email object with body
 */
async function getEmail(emailId) {
  try {
    const response = await resend.emails.get(emailId);
    return response.data;
  } catch (error) {
    console.error('Error fetching email from Resend:', error);
    throw error;
  }
}

/**
 * Send an email via Resend API
 * @param {Object} options - Email options
 * @param {string} options.to - Recipient email address
 * @param {string} options.subject - Email subject
 * @param {string} options.html - HTML content
 * @param {string} [options.text] - Plain text content (optional)
 * @param {string} [options.from] - Sender email (defaults to env var)
 * @returns {Promise<Object>} - Resend API response
 */
async function sendEmail({ to, subject, html, text, from }) {
  try {
    const response = await resend.emails.send({
      from: from || process.env.RESEND_FROM_EMAIL || 'Signals <signals@resend.dev>',
      to: Array.isArray(to) ? to : [to],
      subject,
      html,
      text
    });

    console.log('Email sent successfully:', response.data?.id);
    return response.data;
  } catch (error) {
    console.error('Error sending email via Resend:', error);
    throw error;
  }
}

/**
 * Send a market intelligence report via email
 * @param {string} recipientEmail - The email address to send to
 * @param {Object} report - The formatted report object
 * @param {string} ideaSummary - Brief summary of the idea for subject line
 * @returns {Promise<Object>} - Resend API response
 */
async function sendReport(recipientEmail, report, ideaSummary) {
  const { formatReportEmail } = require('../utils/email');

  const html = formatReportEmail(report);
  const subject = `Signals Report: ${ideaSummary}`;

  return sendEmail({
    to: recipientEmail,
    subject,
    html
  });
}

module.exports = {
  getEmail,
  sendEmail,
  sendReport
};
