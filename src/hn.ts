export type TimeRange = "24h" | "1w" | "2w" | "1m";

export interface HNResult {
  title: string | null;
  url: string | null;
  points: number | null;
  num_comments: number | null;
  created_at: string;
}

interface HNHit {
  title: string | null;
  url: string | null;
  points: number | null;
  num_comments: number | null;
  created_at: string;
}

interface HNSearchResponse {
  hits: HNHit[];
}

const TIME_RANGES: Record<TimeRange, number> = {
  "24h": 24 * 60 * 60,
  "1w": 7 * 24 * 60 * 60,
  "2w": 14 * 24 * 60 * 60,
  "1m": 30 * 24 * 60 * 60,
};

export async function searchHN(
  keywords: string,
  timeRange: TimeRange = "1w"
): Promise<HNResult[]> {
  const cutoff = Math.floor(Date.now() / 1000) - TIME_RANGES[timeRange];

  const params = new URLSearchParams({
    query: keywords,
    tags: "(story,comment)",
    numericFilters: `created_at_i>${cutoff}`,
    hitsPerPage: "5",
  });

  const response = await fetch(
    `https://hn.algolia.com/api/v1/search?${params}`
  );

  if (!response.ok) {
    throw new Error(`HN search failed: ${response.status} ${response.statusText}`);
  }

  const data: HNSearchResponse = await response.json();

  return data.hits.map((hit) => ({
    title: hit.title,
    url: hit.url,
    points: hit.points,
    num_comments: hit.num_comments,
    created_at: hit.created_at,
  }));
}
