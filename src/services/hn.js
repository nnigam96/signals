/**
 * Hacker News Search Service
 * Searches HN via Algolia API
 */

const TIME_RANGES = {
  '24h': 24 * 60 * 60,
  '1w': 7 * 24 * 60 * 60,
  '2w': 14 * 24 * 60 * 60,
  '1m': 30 * 24 * 60 * 60
};

/**
 * Search Hacker News for discussions
 * @param {string} keywords - Search keywords
 * @param {string} timeRange - Time range: '24h', '1w', '2w', '1m'
 * @returns {Promise<Array>} - Array of HN results
 */
async function searchHN(keywords, timeRange = '1w') {
  const cutoff = Math.floor(Date.now() / 1000) - TIME_RANGES[timeRange];

  const params = new URLSearchParams({
    query: keywords,
    tags: '(story,comment)',
    numericFilters: `created_at_i>${cutoff}`,
    hitsPerPage: '10'
  });

  const response = await fetch(
    `https://hn.algolia.com/api/v1/search?${params}`
  );

  if (!response.ok) {
    throw new Error(`HN search failed: ${response.status} ${response.statusText}`);
  }

  const data = await response.json();

  return data.hits.map(hit => ({
    title: hit.title || hit.story_title || 'Untitled',
    url: hit.url || `https://news.ycombinator.com/item?id=${hit.objectID}`,
    points: hit.points || 0,
    num_comments: hit.num_comments || 0,
    created_at: hit.created_at
  }));
}

module.exports = {
  searchHN,
  TIME_RANGES
};
