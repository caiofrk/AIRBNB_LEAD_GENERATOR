---
description: Scraper v2.0 architecture - LOCKED decisions, do not change
---

# Scraper v2.0 — LOCKED Architecture

**DO NOT CHANGE THESE CORE DECISIONS. They were hard-won through debugging.**

## Host Profile Navigation (THE BIG ONE)

### How to find the HOST (not a commenter):
1. Search raw page source for `/users/(show|profile)/{id}?...PdpHomeMarketplace`
2. Only the HOST's link has `PdpHomeMarketplace` — reviewers NEVER do
3. If not found, search for `"hostId": "{id}"` in page JSON data

### How to navigate to the host profile:
- **USE**: `/users/profile/{host_id}?previous_page_name=PdpHomeMarketplace`
- **NEVER USE**: `/users/show/{host_id}` — this REDIRECTS TO LOGIN for unauthenticated browsers!
- Always check if landed URL contains `/login` — if so, the URL format is wrong

### How to find the host section on a listing page:
- Primary: `div[data-section-id="HOST_OVERVIEW_DEFAULT"]`
- Fallbacks: `HOST_PROFILE_DEFAULT`, `pdp-host-profile-section`
- Last resort: text search for "anfitrião", "anfitriã", "hosted by", "superhost"
- The host section uses `<button>` elements, NOT `<a>` links!

## Scrape Flow
- `pending` → deep_analyze_listing → `ready`
- NO intermediate states, NO AI dependency
- Status goes directly to `ready` after scraping

## Commands
- `python scraper.py watcher` — polls for pending leads, scrapes them
- `python scraper.py search` — discovers new leads from neighborhoods, then scrapes
- `python scraper.py deep` — one-off scrape of all pending
- `python scraper.py <URL>` — scrape a single listing

## Language Support
- Superhost: "superhost", "superanfitrião", "superanfitriã"
- Host name patterns: "Hosted by", "Hospede-se com", "Anfitrião"

## Git Tag
- `v2.0` — LOCKED version with working host profile scraping
