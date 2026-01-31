Signals — AI-Powered Market Intelligence  Turn any company name or pitch deck into verified intelligence in seconds. Real-time web crawling, document parsing, and AI analysis — stored, searchable, and always updating.  Built at Hack the Stackathon @ YC HQ. Powered by Firecrawl, Reducto, MongoDB, OpenRouter, Supabase, and Resend.


- [x] ~~Create Express/FastAPI server with health check endpoint~~
- [x] ~~Set up Resend inbound webhook at `/webhook/email`~~
- [x] ~~Parse webhook payload to extract email body text~~
- [x] ~~Call Resend API to fetch full email body (webhook only sends metadata)~~
- [ ] Write Claude prompt: extract `{domain, problem, keywords[], competitors_mentioned[]}` from raw idea text
- [ ] Test: send email "AI tool for extracting renewal dates from SaaS contracts" → log parsed output
- [ ] Store parsed idea in MongoDB `ideas` collection
- [ ] Register for Semantic Scholar API (free, no key needed for basic)
- [ ] Write function `searchPapers(keywords)` → hits `/paper/search` endpoint
- [ ] Extract: `{title, abstract, citationCount, year, url}` for top 5 results
- [ ] Handle empty results gracefully (some ideas won't have papers)
- [ ] Test: search "contract extraction NLP" → log 5 papers
- [ ] Store papers in MongoDB under `idea.research.papers`
- [x] ~~Write function `searchHN(keywords)` → hits Algolia HN API (`hn.algolia.io/api/v1/search`)~~
- [x] ~~Filter to stories + comments from last 2 years~~
- [x] ~~Extract: `{title, url, points, num_comments, created_at}` for top 5~~
- [ ] Write function `scrapeTechmeme()` → Firecrawl scrape of techmeme.com homepage
- [ ] Extract recent headlines mentioning keywords (simple string match)
- [ ] Test: search "SaaS contracts" on HN → log 5 threads
- [ ] Store HN results in MongoDB under `idea.research.hn_discussions`
- [ ] Store Techmeme hits in MongoDB under `idea.research.tech_news`
- [ ] Write function `searchCompetitors(domain, keywords)` → Firecrawl search API
- [ ] Query: `"{domain}" startup OR tool OR software`
- [ ] Extract: `{name, url, snippet}` for top 5 results
- [ ] Write function `scrapeProductHunt(keywords)` → Firecrawl scrape of PH search
- [ ] Extract: `{name, tagline, url, upvotes}` for top 5
- [ ] Dedupe competitors by domain
- [ ] Test: search "contract management" → log 5 competitors
- [ ] Store competitors in MongoDB under `idea.research.competitors`
- [ ] Write function `getMarketSignals(company_names)` → for each competitor:
  - [ ] Firecrawl scrape company homepage → extract recent news/blog
  - [ ] Firecrawl search `"{company}" funding OR raised OR hiring` → extract signals
- [ ] Extract: `{company, signal_type, description, date, source_url}`
- [ ] Store signals in MongoDB under `idea.research.market_signals`
- [ ] Generate Voyage embedding for full research blob (for future similarity search)
- [ ] Store embedding in MongoDB under `idea.embedding`
- [ ] Write Claude prompt: synthesize all research into structured report
- [ ] Sections: Executive Summary, Academic Research, Community Discussion, Competitive Landscape, Market Signals, Recommendation
- [ ] Require citations: every claim links to source
- [ ] Output as JSON with sections (not raw markdown)
- [ ] Test: pass full research object → log structured report
- [ ] Store report in MongoDB under `idea.report`
- [x] ~~Write function `formatReportEmail(report)` → converts JSON to HTML email~~
- [x] ~~Style: clean, scannable, mobile-friendly~~
- [x] ~~Include section headers, bullet points, clickable links~~
- [x] ~~Add verdict banner at top: "VALIDATED ✅" / "NEEDS MORE RESEARCH 🔍" / "CROWDED MARKET ⚠️"~~
- [x] ~~Send via Resend to original sender's email~~
- [ ] Test: trigger full flow → receive email in inbox
- [ ] Measure end-to-end latency (target: <60s)
- [ ] Pre-cache 3 example ideas with full research:
  - [ ] "AI tool for extracting renewal dates from SaaS contracts"
  - [ ] "Competitive intelligence dashboard for startups"
  - [ ] "Voice cloning for podcast ads"
- [ ] Write demo script (90 seconds)
- [ ] Test Resend inbound with real email forward
- [ ] Add error handling: timeout fallbacks, empty results messaging
- [ ] Create 1-slide pitch: problem → solution → demo → stack
- [ ] Dry run demo 2x

**Minimum viable demo:**
- Email in → parsed idea
- HN results + competitors
- Claude-generated summary
- Email out

---

## API Reference

```
Semantic Scholar: https://api.semanticscholar.org/graph/v1/paper/search?query={keywords}
HN Algolia: https://hn.algolia.com/api/v1/search?query={keywords}&tags=story
Firecrawl Search: POST https://api.firecrawl.dev/v1/search
Firecrawl Scrape: POST https://api.firecrawl.dev/v1/scrape
Resend Inbound: webhook → GET https://api.resend.com/emails/{id}
Resend Send: POST https://api.resend.com/emails
Voyage Embed: POST https://api.voyageai.com/v1/embeddings
```

---

## Credentials Needed

- [ ] Firecrawl API key (coupon: HACKTHESTACKATHON)
- [ ] Resend API key (coupon: sfh4cks)
- [ ] MongoDB Atlas connection string
- [ ] Voyage AI API key
- [ ] Anthropic API key (for Claude)
- [ ] (Optional) OpenRouter key if using multi-model

Contributors: @nnigam96 @zubair
