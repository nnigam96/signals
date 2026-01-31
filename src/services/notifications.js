const { sendEmail } = require('./resend');
const templates = require('../utils/emailTemplates');

/**
 * Notification types for the dashboard
 */
const NotificationType = {
  SIGNUP_CONFIRMATION: 'signup_confirmation',
  DASHBOARD_READY: 'dashboard_ready',
  PROGRESS_UPDATE: 'progress_update'
};

/**
 * Progress stages for real-time updates
 */
const ProgressStage = {
  PARSING_INPUT: 'parsing_input',
  SEARCHING_PAPERS: 'searching_papers',
  SEARCHING_DISCUSSIONS: 'searching_discussions',
  FINDING_COMPETITORS: 'finding_competitors',
  ANALYZING_MARKET: 'analyzing_market',
  GENERATING_REPORT: 'generating_report',
  COMPLETE: 'complete'
};

const stageDescriptions = {
  [ProgressStage.PARSING_INPUT]: 'Analyzing your input...',
  [ProgressStage.SEARCHING_PAPERS]: 'Searching academic research...',
  [ProgressStage.SEARCHING_DISCUSSIONS]: 'Finding community discussions...',
  [ProgressStage.FINDING_COMPETITORS]: 'Identifying competitors...',
  [ProgressStage.ANALYZING_MARKET]: 'Analyzing market signals...',
  [ProgressStage.GENERATING_REPORT]: 'Generating your report...',
  [ProgressStage.COMPLETE]: 'Your dashboard is ready!'
};

/**
 * Send sign-up confirmation email
 * @param {string} email - User's email address
 * @param {string} dashboardId - ID of the dashboard being generated
 * @returns {Promise<Object>} - Resend API response
 */
async function sendSignupConfirmation(email, dashboardId) {
  const html = templates.signupConfirmation({ email, dashboardId });

  return sendEmail({
    to: email,
    subject: 'Welcome to Signals - Your dashboard is being prepared',
    html
  });
}

/**
 * Send dashboard ready notification
 * @param {string} email - User's email address
 * @param {Object} options - Dashboard details
 * @param {string} options.dashboardId - Dashboard ID
 * @param {string} options.dashboardUrl - URL to access the dashboard
 * @param {string} options.ideaSummary - Brief summary of the analyzed idea
 * @param {string} options.verdict - VALIDATED, NEEDS_RESEARCH, or CROWDED
 * @returns {Promise<Object>} - Resend API response
 */
async function sendDashboardReady(email, { dashboardId, dashboardUrl, ideaSummary, verdict }) {
  const html = templates.dashboardReady({
    dashboardId,
    dashboardUrl,
    ideaSummary,
    verdict
  });

  return sendEmail({
    to: email,
    subject: `Your Signals dashboard is ready: ${ideaSummary}`,
    html
  });
}

/**
 * Send progress update email
 * @param {string} email - User's email address
 * @param {Object} options - Progress details
 * @param {string} options.dashboardId - Dashboard ID
 * @param {string} options.stage - Current progress stage
 * @param {number} options.progress - Progress percentage (0-100)
 * @param {Object} [options.data] - Optional data found in this stage
 * @returns {Promise<Object>} - Resend API response
 */
async function sendProgressUpdate(email, { dashboardId, stage, progress, data }) {
  const stageDescription = stageDescriptions[stage] || stage;

  const html = templates.progressUpdate({
    dashboardId,
    stage,
    stageDescription,
    progress,
    data
  });

  return sendEmail({
    to: email,
    subject: `Signals Update: ${stageDescription} (${progress}%)`,
    html
  });
}

/**
 * Batch notify multiple users about a dashboard update
 * @param {string[]} emails - Array of email addresses
 * @param {string} notificationType - Type of notification
 * @param {Object} data - Notification data
 * @returns {Promise<Object[]>} - Array of Resend API responses
 */
async function notifyUsers(emails, notificationType, data) {
  const notifications = emails.map(email => {
    switch (notificationType) {
      case NotificationType.SIGNUP_CONFIRMATION:
        return sendSignupConfirmation(email, data.dashboardId);
      case NotificationType.DASHBOARD_READY:
        return sendDashboardReady(email, data);
      case NotificationType.PROGRESS_UPDATE:
        return sendProgressUpdate(email, data);
      default:
        throw new Error(`Unknown notification type: ${notificationType}`);
    }
  });

  return Promise.all(notifications);
}

module.exports = {
  NotificationType,
  ProgressStage,
  stageDescriptions,
  sendSignupConfirmation,
  sendDashboardReady,
  sendProgressUpdate,
  notifyUsers
};
