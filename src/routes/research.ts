import { Router, Request, Response } from "express";
import { searchHN, TimeRange, HNResult } from "../hn";

const router = Router();

const validTimeRanges: TimeRange[] = ["24h", "1w", "2w", "1m"];

function isValidTimeRange(value: string): value is TimeRange {
  return validTimeRanges.includes(value as TimeRange);
}

router.get("/hn", async (req: Request, res: Response) => {
  const keywords = req.query.keywords as string | undefined;
  const timeRange = (req.query.timeRange as string) || "1w";

  if (!keywords) {
    res.status(400).json({ error: "keywords query parameter is required" });
    return;
  }

  if (!isValidTimeRange(timeRange)) {
    res.status(400).json({
      error: `Invalid timeRange. Must be one of: ${validTimeRanges.join(", ")}`,
    });
    return;
  }

  try {
    const results: HNResult[] = await searchHN(keywords, timeRange);
    res.json({ results });
  } catch (error) {
    console.error("HN search error:", error);
    res.status(500).json({ error: "Failed to search Hacker News" });
  }
});

export default router;
