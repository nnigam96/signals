import { Router, Request, Response } from "express";
import { randomUUID } from "crypto";

const router = Router();

// In-memory job storage (replace with MongoDB later)
const jobs = new Map<
  string,
  {
    id: string;
    status: "pending" | "processing" | "completed" | "failed";
    progress: number;
    query?: string;
    createdAt: Date;
  }
>();

// POST /api/search - Submit a search query
router.post("/", async (req: Request, res: Response) => {
  const { query } = req.body;

  if (!query) {
    res.status(400).json({ error: "query is required" });
    return;
  }

  const jobId = randomUUID();
  jobs.set(jobId, {
    id: jobId,
    status: "pending",
    progress: 0,
    query,
    createdAt: new Date(),
  });

  // Simulate async processing (replace with real processing later)
  simulateProcessing(jobId);

  res.status(201).json({ jobId });
});

// GET /api/job/:jobId/status - Get job status
router.get("/job/:jobId/status", async (req: Request<{ jobId: string }>, res: Response) => {
  const { jobId } = req.params;
  const job = jobs.get(jobId);

  if (!job) {
    res.status(404).json({ error: "Job not found" });
    return;
  }

  res.json({
    id: job.id,
    status: job.status,
    progress: job.progress,
    isComplete: job.status === "completed",
  });
});

// Simulate processing (temporary until real implementation)
function simulateProcessing(jobId: string) {
  const job = jobs.get(jobId);
  if (!job) return;

  job.status = "processing";

  const steps = [20, 40, 60, 80, 100];
  let stepIndex = 0;

  const interval = setInterval(() => {
    const currentJob = jobs.get(jobId);
    if (!currentJob) {
      clearInterval(interval);
      return;
    }

    currentJob.progress = steps[stepIndex];
    stepIndex++;

    if (stepIndex >= steps.length) {
      currentJob.status = "completed";
      clearInterval(interval);
    }
  }, 1000);
}

export default router;
