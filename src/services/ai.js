const Anthropic = require('@anthropic-ai/sdk');

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY
});

/**
 * Extract business idea from email content using Claude
 * @param {string} emailBody - The email body text
 * @param {string} subject - The email subject
 * @returns {Promise<Object>} - Extracted idea details
 */
async function extractIdea(emailBody, subject) {
  const message = await anthropic.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 1024,
    messages: [
      {
        role: 'user',
        content: `Extract the business idea from this email. Return a JSON object with:
- summary: A one-sentence summary of the idea (max 100 chars)
- description: A detailed description of the idea
- keywords: Array of 3-5 keywords for research
- industry: The primary industry/sector

Email Subject: ${subject}

Email Body:
${emailBody}

Respond only with valid JSON, no markdown.`
      }
    ]
  });

  try {
    const text = message.content[0].text;
    return JSON.parse(text);
  } catch (error) {
    console.error('Failed to parse AI response:', error);
    return {
      summary: subject || 'Business idea analysis',
      description: emailBody,
      keywords: ['startup', 'business', 'market'],
      industry: 'Technology'
    };
  }
}

/**
 * Analyze market data and generate a verdict
 * @param {Object} data - Research data (papers, discussions, competitors)
 * @param {string} ideaSummary - The idea being analyzed
 * @returns {Promise<Object>} - Analysis with verdict
 */
async function analyzeMarket(data, ideaSummary) {
  const { papers = [], discussions = [], competitors = [] } = data;

  const message = await anthropic.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 2048,
    messages: [
      {
        role: 'user',
        content: `Analyze this market research data for the idea: "${ideaSummary}"

Academic Papers Found: ${papers.length}
${papers.slice(0, 5).map(p => `- ${p.title}`).join('\n')}

Community Discussions (HN): ${discussions.length}
${discussions.slice(0, 5).map(d => `- ${d.title} (${d.points} points)`).join('\n')}

Competitors Identified: ${competitors.length}
${competitors.slice(0, 5).map(c => `- ${c.name}: ${c.description || 'N/A'}`).join('\n')}

Provide analysis in JSON format:
{
  "verdict": "VALIDATED" | "NEEDS_RESEARCH" | "CROWDED",
  "confidence": 0-100,
  "summary": "2-3 sentence executive summary",
  "opportunities": ["opportunity 1", "opportunity 2"],
  "risks": ["risk 1", "risk 2"],
  "recommendations": ["recommendation 1", "recommendation 2"]
}

VALIDATED = Strong market opportunity with limited competition
NEEDS_RESEARCH = Promising but needs more validation
CROWDED = Highly competitive market, differentiation needed

Respond only with valid JSON.`
      }
    ]
  });

  try {
    const text = message.content[0].text;
    return JSON.parse(text);
  } catch (error) {
    console.error('Failed to parse market analysis:', error);
    return {
      verdict: 'NEEDS_RESEARCH',
      confidence: 50,
      summary: 'Unable to complete full analysis. Manual review recommended.',
      opportunities: [],
      risks: [],
      recommendations: ['Conduct additional market research']
    };
  }
}

/**
 * Generate a comprehensive report from all research data
 * @param {Object} idea - Extracted idea details
 * @param {Object} research - Research data (papers, discussions, competitors)
 * @param {Object} analysis - Market analysis with verdict
 * @returns {Promise<Object>} - Complete report
 */
async function generateReport(idea, research, analysis) {
  return {
    ideaSummary: idea.summary,
    ideaDescription: idea.description,
    industry: idea.industry,
    keywords: idea.keywords,
    verdict: analysis.verdict,
    confidence: analysis.confidence,
    executiveSummary: analysis.summary,
    academicResearch: {
      count: research.papers?.length || 0,
      papers: research.papers?.slice(0, 10) || []
    },
    communityDiscussions: {
      count: research.discussions?.length || 0,
      discussions: research.discussions?.slice(0, 10) || []
    },
    competitiveLandscape: {
      count: research.competitors?.length || 0,
      competitors: research.competitors?.slice(0, 10) || []
    },
    opportunities: analysis.opportunities,
    risks: analysis.risks,
    recommendations: analysis.recommendations,
    generatedAt: new Date().toISOString()
  };
}

module.exports = {
  extractIdea,
  analyzeMarket,
  generateReport
};
