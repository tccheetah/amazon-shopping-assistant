# Amazon Shopping Assistant - Design Doc

## Overview

This doc outlines the approach for the Amazon Shopping Assistant. Started with v0 implementation and added v1 enhancements to support queries beyond Amazon's standard filters.

## Components

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
Navigates Amazon, applies filters, extracts product data. Fixed the "Unknown Title" issue by adding multiple fallback selectors and extraction approaches.

### QueryParser
Converts natural language to structured params. Now supports advanced parameter extraction for:
- Exact rating thresholds (4.7 stars)
- Country of origin ("made in Italy")
- Material specifications
- Excluded terms ("without BPA")

### ProductAnalyzer
Ranks products using weighted scoring based on ratings, reviews, price, etc. v1 adds:
- Post-search filtering for exact rating thresholds
- Country of origin filtering
- Material filtering
- Enhanced relevance scoring

### ConversationManager
Controls flow, maintains context, and handles follow-ups. v1 adds context tracking and better suggestions.

## Technical Decisions

### Why Playwright?
- Faster than Selenium
- Better auto-waiting for elements
- Cleaner API
- Better handling of modern web features

Web scraping alone would be too limited for interactive browsing imo.

### Detection Avoidance
- Random delays between actions
- Human-like typing (char by char)
- Mouse movement simulation
- User agent config

### Query Understanding
Now extracts parameters not directly supported by Amazon filters:
- Exact star ratings (like 4.7 stars)
- Country of origin
- Material specifications
- Features to exclude

### Ranking Algorithm
Weighted scoring:
- Rating (30%)
- Reviews (20%)
- Price (20%)
- Prime (10%)
- Relevance (20%)

Now supports post-filtering of results to handle requirements that Amazon filters don't support directly.

## Project Roadmap & Milestones

### v0 (original)
- Basic filters
- Regex parsing
- Simple scoring
- Basic conversation

### v1 (current)
- Fixed product extraction with multiple selectors
- Enhanced scoring system with better relevance matching
- Advanced filtering beyond Amazon's limitations
- Support for exact rating thresholds, country of origin, materials
- Follow-up detection and context tracking
- Better response formatting and suggestions

### v2 (later)
- AI-powered query understanding
- Planning and multi-step workflows
- User preference learning
- Proactive refinements
- Comparative analysis
Success criteria: Makes decisions a knowledgeable shopper would make

Critical path: Query understanding → Conversation handling → Product comparison

Risks:
- Amazon UI changes: Mitigate with fallback selectors & monitoring
- Rate limiting: Implement session pooling & backoff strategies
- Parsing failures: Build robust fallbacks to regex when AI fails

## Resource Planning

### Infrastructure
- Development: Basic cloud VMs for testing ($500/mo guesstimate but varies wildly (can also cut down costs pretty well))
- Production: Auto-scaling containers ($2-5K/mo based on usage ^)
- LLM API costs: ~$0.50-1 per complex user session (can look into better LLMs to use too or vary depending on the query type)
- Proxies/browser services: $2K/mo at scale (depends on your scale)
- All costs here are from a very surface level search on prices

### Technical Debt Considerations
- Plan refactor after v1 for scaling architecture
- Schedule regular selector maintenance for Amazon UI changes
- Allocate 20% of sprint capacity to testing & stability

## v1 Implementation Notes

Enhanced features added:
1. Solved "Unknown Title" bug with multiple fallback selectors in AmazonNavigator
2. Added support for exact rating thresholds (e.g., 4.7 stars vs just 4 stars & up)
3. Implemented country of origin filtering (e.g., "made in Italy")
4. Added material detection and filtering
5. Enhanced ProductAnalyzer with better scoring that considers more factors
6. Added follow-up detection to ConversationManager for more natural conversations
7. Improved response formatting with contextual suggestions
8. Added support for refining previous searches

These changes maintain the same interfaces as v0 for backward compatibility while significantly improving functionality beyond what Amazon's filters directly support.

## Evaluation & Testing

### Current Testing Approach
- Manual CLI testing
- Unit tests for individual components once I get to it
- Testing with advanced queries like "coffee makers with over 4.7 stars and made in Italy"
- Future: regression tests, performance benchmarks

### Helpfulness Metrics
- Success rate: % of requests with satisfactory results
- Decision quality: % of recommendations matching expert shoppers
- Time saved: vs. manual shopping for same request is the big one

### User Feedback
- In-app satisfaction ratings
- A/B testing different ranking algorithms
- Capture refinement requests as signal for improvement

## Key Challenges & Solutions

### Dynamic Layout
Solution: Multiple fallback selectors for key elements

### Detection Risk
Solution: Human-like behavior, random delays

### Advanced Filtering Beyond Amazon's UI
Solution: Extract rich parameters from queries and apply post-search filtering

### Ambiguous Queries
Solution: Conservative parsing with better keyword extraction

### Scaling Challenges
- Serverless architecture for burst capacity
- Browser instance pooling
- Caching common searches and product data
- Queue system for high-demand periods

## Future Improvements

### Additional Features
- Price history tracking and alerts
- Deal hunting capabilities
- Cross-site comparison
- Barcode/image search capability
- Voice interface for mobile

### Product Understanding
- Category-specific attribute extraction
- Custom embeddings for products and requests
- Comparison tables for similar items
- Expert knowledge integration for specialized categories

## Next Steps

1. Complete unit tests 
2. Add error recovery for common failures as Lewis said
3. Add AI-based query parsing for v2
4. Implement product comparison feature
5. Give user warning about the robot checker