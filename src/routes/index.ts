import { Router } from "express";
import researchRouter from "./research";
import searchRouter from "./search";

const router = Router();

router.use("/research", researchRouter);
router.use("/search", searchRouter);

// Mount job status under /api as well
router.use("/", searchRouter);

export default router;
