# Amazon Shopping Assistant - Design Doc

## Overview

This doc outlines the approach for the Amazon Shopping Assistant. I've implemented v0 with hooks for v1 and v2 enhancements.

## Components (wrote on paper then generated)

```
User -> ConversationManager -> QueryParser -> AmazonNavigator -> BrowserManager -> Amazon.com
                                                          ^                              |
                                                          |                              v
                                                          +------ ProductAnalyzer <- Product Results
                                                                       |
                                                                       v
                                                                 User Response
```

### BrowserManager
Handles browser automation with Playwright. Manages sessions and implements anti-detection.

### AmazonNavigator
Navigates Amazon, applies filters, extracts product data. Built with flexible selectors.

### QueryParser
Converts natural language to structured params using regex for v0. AI parser is ready for v1.

### ProductAnalyzer
Ranks products using a weighted score system based on ratings, reviews, price, etc.

### ConversationManager
Controls flow, maintains context, handles follow-ups, formats responses.

## Technical Decisions

### Why Playwright?
- Cleaner and faster than Selenium from searches
- Better auto-waiting for elements
- Better handling of modern web features

Web scraping alone would be too limited for interactive browsing.

### Detection Avoidance
- Random delays between actions
- Human-like typing (char by char)
- Mouse movement simulation
- User agent config

### Query Understanding (v0)
Using regex to extract:
- Product type
- Price range
- Rating requirements
- Prime preference
- Keywords

### Ranking Algorithm
Simple weighted scoring:
- Rating (40%)
- Reviews (20%) 
- Price (20%)
- Prime (10%)
- Relevance (10%)

## Version Roadmap from Lewis expanded

### v0 (current)
- Basic filters
- Regex parsing
- Simple scoring
- Basic conversation

### v1 
- Enable AI query parser (already coded)
- Handle custom criteria
- Better conversation context
- Improved ranking
- Enhanced fingerprinting

### v2
- Planning and multi-step workflows
- User preference learning
- Proactive refinements
- Comparative analysis
- Self-improvement

## Challenges & Solutions

### Dynamic Layout
Solution: Multiple fallback selectors for key elements

### Detection Risk
Solution: Human-like behavior, random delays

### Ambiguous Queries
Solution: Conservative parsing in v0, AI in v1

## Testing Approach

- Manual CLI testing
- Unit tests for individual components
- Future: regression tests, performance benchmarks

## Next Steps

1. Complete unit tests 
2. Add error recovery for common failures
3. Enable AI parsing as v1 feature flag
4. Improve response formatting
5. Add browser fingerprinting enhancements