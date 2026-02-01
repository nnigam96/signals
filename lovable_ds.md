# Data Models Schema

Comprehensive schema documentation for all data models in the Signals Intelligence platform.

---

## Core Entities

### Company

Primary entity representing a target company in the market intelligence system.

```typescript
interface Company {
  id: string;                              // UUID - unique identifier
  name: string;                            // Company display name
  sector: string;                          // Industry sector (e.g., "AI/ML", "Fintech")
  location: string;                        // HQ location (city, country)
  employees: string;                       // Employee count range (e.g., "50-200")
  signal?: string;                         // Current active signal type
  signalStrength?: "high" | "medium" | "low"; // Signal confidence level
  
  // Extended fields (future)
  website?: string;                        // Company website URL
  founded?: number;                        // Year founded
  funding?: string;                        // Total funding raised
  lastFundingRound?: string;               // Most recent round type
  description?: string;                    // Company description
  tags?: string[];                         // Classification tags
  createdAt?: string;                      // ISO 8601 timestamp
  updatedAt?: string;                      // ISO 8601 timestamp
}
```

---

## Search & Jobs

### SearchRequest

Payload for initiating a market search.

```typescript
interface SearchRequest {
  query: string;                           // Natural language search query
  filters?: {
    sectors?: string[];                    // Filter by sectors
    locations?: string[];                  // Filter by geography
    employeeRange?: {
      min?: number;
      max?: number;
    };
    signals?: string[];                    // Filter by signal types
  };
}
```

### SearchResponse

Response when a search job is created.

```typescript
interface SearchResponse {
  jobId: string;                           // UUID for tracking the job
}
```

### JobStatus

Polling response for job progress.

```typescript
interface JobStatus {
  id: string;                              // Job UUID
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;                        // 0-100 percentage
  isComplete: boolean;                     // Convenience flag
  error?: string;                          // Error message if failed
  estimatedTimeRemaining?: number;         // Seconds remaining (optional)
}
```

### SearchResults

Final results payload when job completes.

```typescript
interface SearchResults {
  companies: Company[];                    // All matched companies
  signals: Record<string, Company[]>;      // Companies grouped by signal type
  metadata?: {
    totalMatches: number;
    queryTokens: string[];
    searchDurationMs: number;
  };
}
```

---

## Signals & Intelligence

### Signal

A detected market signal associated with a company.

```typescript
interface Signal {
  id: string;                              // UUID
  companyId: string;                       // FK to Company
  type: SignalType;                        // Signal classification
  strength: "high" | "medium" | "low";     // Confidence level
  source: string;                          // Data source (e.g., "HN", "LinkedIn")
  sourceUrl?: string;                      // Link to source
  headline: string;                        // Signal summary
  details?: string;                        // Extended context
  detectedAt: string;                      // ISO 8601 timestamp
  expiresAt?: string;                      // Signal validity window
}

type SignalType =
  | "leadership_change"
  | "funding_round"
  | "expansion"
  | "product_launch"
  | "hiring_surge"
  | "partnership"
  | "acquisition"
  | "tech_adoption"
  | "market_entry"
  | "regulatory_change";
```

### HNResult

Hacker News research data point.

```typescript
interface HNResult {
  title: string | null;                    // Post title
  url: string | null;                      // Link URL
  points: number | null;                   // Upvotes
  num_comments: number | null;             // Comment count
  created_at: string;                      // ISO 8601 timestamp
}
```

---

## Notifications

### EmailSubscription

User subscription for job completion notifications.

```typescript
interface EmailSubscription {
  id: string;                              // UUID
  jobId: string;                           // FK to Job
  email: string;                           // Subscriber email
  status: "pending" | "sent" | "failed";   // Delivery status
  createdAt: string;                       // ISO 8601 timestamp
  sentAt?: string;                         // When notification was sent
}
```

### NotificationPayload

Email notification content.

```typescript
interface NotificationPayload {
  to: string;                              // Recipient email
  subject: string;                         // Email subject
  jobId: string;                           // Reference job
  resultsUrl: string;                      // Link to view results
  summary: {
    totalCompanies: number;
    topSignals: string[];
    highlightedCompanies: Array<{
      name: string;
      signal: string;
    }>;
  };
}
```

---

## User & Watchlist

### User

Platform user (future authentication).

```typescript
interface User {
  id: string;                              // UUID
  email: string;                           // Unique email
  name?: string;                           // Display name
  role: "viewer" | "analyst" | "admin";    // Access level
  preferences?: UserPreferences;
  createdAt: string;                       // ISO 8601 timestamp
  lastLoginAt?: string;                    // Last activity
}

interface UserPreferences {
  defaultSectors?: string[];               // Preferred sectors to track
  emailFrequency: "realtime" | "daily" | "weekly";
  signalThreshold: "all" | "medium" | "high"; // Minimum signal strength
}
```

### WatchlistItem

Company added to user's watchlist.

```typescript
interface WatchlistItem {
  id: string;                              // UUID
  userId: string;                          // FK to User
  companyId: string;                       // FK to Company
  notes?: string;                          // User notes
  alertsEnabled: boolean;                  // Receive signal alerts
  addedAt: string;                         // ISO 8601 timestamp
}
```

---

## Form Validation Schemas (Zod)

### Email Schema

```typescript
import { z } from "zod";

export const emailSchema = z.object({
  email: z.string().email({ message: "Please enter a valid email address" }),
});

export type EmailFormData = z.infer<typeof emailSchema>;
```

### Search Schema

```typescript
export const searchSchema = z.object({
  query: z.string().min(1, { message: "Please enter a search query" }),
});

export type SearchFormData = z.infer<typeof searchSchema>;
```

---

## API Endpoints Reference

| Method | Endpoint | Request Body | Response |
|--------|----------|--------------|----------|
| GET | `/health` | - | `{ status, timestamp }` |
| POST | `/api/search` | `SearchRequest` | `SearchResponse` |
| GET | `/api/job/:id/status` | - | `JobStatus` |
| GET | `/api/job/:id/results` | - | `SearchResults` |
| POST | `/api/notify/subscribe` | `{ jobId, email }` | `{ success: boolean }` |
| GET | `/api/company/:id` | - | `Company` |
| GET | `/api/company/:id/signals` | - | `Signal[]` |
| GET | `/api/research/hn` | `?keywords&timeRange` | `{ results: HNResult[] }` |

---

## Database Tables (Relational)

```sql
-- Core tables
companies (id, name, sector, location, employees, website, founded, created_at, updated_at)
signals (id, company_id, type, strength, source, headline, detected_at, expires_at)
jobs (id, query, status, progress, created_at, completed_at)
job_results (id, job_id, company_id, signal_type)

-- Notifications
email_subscriptions (id, job_id, email, status, created_at, sent_at)

-- User management (future)
users (id, email, name, role, preferences, created_at, last_login_at)
watchlist_items (id, user_id, company_id, notes, alerts_enabled, added_at)
```
