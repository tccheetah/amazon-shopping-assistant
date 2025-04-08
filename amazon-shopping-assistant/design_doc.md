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
Handles all the browser automation with Playwright. After trying a few approaches, I settled on a mix of these anti-detection techniques:
- Random delays between actions (configurable, but usually 1-3s)
- Typing character by character like a human would
- Mouse movement simulation (still needs work but helps)
- User agent configuration
- Session recovery when something breaks

I spent way too long comparing Playwright vs Selenium, but Playwright was definitely worth it - especially for the auto-waiting features which saved me tons of headaches with timing issues.

### AmazonNavigator
This component handles Amazon navigation, applying filters, and extracting product data. I had to spend a lot of time fixing the "Unknown Title" bug with multiple fallback selectors. Now it includes:
- 3-4 different selectors for each important element
- Link extraction that properly handles ASINs
- Multiple strategies for price and rating extraction
- Error handling for when Amazon decides to change things around

### QueryParser
Converts natural language to structured parameters. This part was actually pretty fun to build. It now extracts:
- Exact rating thresholds (4.7 stars vs just 4+ stars) - this was surprisingly useful
- Country of origin ("made in Italy")
- Material specs ("leather", "aluminum")
- Excluded terms ("without BPA")

The regex patterns got pretty complex but work better than expected!

### ProductAnalyzer
Ranks products using a weighted scoring system:
- Rating (30%)
- Reviews (20%)
- Price (20%)
- Prime (10%)
- Relevance (20%)

I spent a while tuning these weights - the log scaling for review counts made a big difference (otherwise products with 10,000+ reviews always dominated).

### ProductResearcher (V2)
This is a completely new component that does deep product analysis:
- Extracts specs from product pages (tricky with all the different formats)
- Analyzes reviews for sentiment and key points
- Generates pros/cons lists based on specs and reviews
- Creates synthetic analysis when review data is limited

Had some issues with "No review text found" that I fixed by implementing fallback analysis based on product descriptions.

### AgentFramework (V2)
Another new component providing real agent capabilities:
- Multi-step planning for complex requests
- User preference tracking
- Research prioritization based on product type and price
- Comparison logic for similar products
- Auto-generated refinement suggestions

Still working on making this more reliable, but it works surprisingly well for most queries.

### ConversationManager
Controls the conversation flow and context:
- Tracks context across multiple turns (harder than I expected)
- Detects follow-up questions pretty reliably
- Formats responses with useful next steps
- Handles errors gracefully

## Technical Decisions

### Why Playwright?
After experimenting with both, Playwright was:
- Much faster than Selenium (50-60% in my testing)
- Way better at waiting for elements automatically
- Cleaner API (especially with TypeScript if I use it later)
- Better at handling modern web stuff

I considered just web scraping, but you really need browser automation for the filters and navigation.

### Detection Avoidance
Amazon's pretty aggressive with bot detection, so I implemented:
- Random delays between actions
- Character-by-character typing with tiny random pauses
- Mouse movement (still feels a bit robotic but helps)
- User agent configs
- Session spreading when possible

### Query Understanding
I was surprised how much I could extract beyond Amazon's basic filters:
- Exact star ratings like 4.7 (Amazon only does whole stars)
- Country of origin
- Materials
- Things to exclude

All of this goes into post-filtering since Amazon's UI doesn't support it directly.

### User Personalization (V2)
I've started implementing:
- Simple preference storage by session
- Weighted tracking (purchases > views)
- Category-specific preferences
- Preference-adjusted scoring

Still pretty basic but shows the direction.

## Project Roadmap & Milestones

### V0 (completed)
- Basic search capabilities
- Simple regex parsing
- Rudimentary scoring
- Command-line conversation
Timeline: Took about 2 days
Success criteria: ✓ Found basic products with clear parameters

### V1 (completed)
- Fixed major extraction bugs
- Better scoring system
- Advanced filtering beyond Amazon's UI
- Added exact ratings, origin, materials filtering
- Basic conversation context
- Improved formatting
Timeline: Around 3 days
Success criteria: ✓ Handled complex filtering and maintained basic conversation

### V2 (current)
- AI-powered query understanding
- Multi-step planning
- User preference tracking
- Proactive suggestions
- Deep product research
- Comparative analysis
Timeline: About 5 days
Success criteria: ✓ Makes decisions similar to a knowledgeable shopper

### V3 (future)
- Cross-site comparison (Amazon, Walmart, Target)
- Price tracking
- Social proof integration
- Voice interface
- AR integration for physical shopping
Timeline: Probably 8 weeks
Success criteria: Becomes preferred shopping method for repeat users

The critical path really follows:
1. Query understanding → 
2. Conversation handling → 
3. Product research → 
4. Comparison system → 
5. Cross-site integration

Main risks I'm worried about:
- Amazon changing their UI (happens constantly)
- Getting rate limited/blocked
- Parsing failures on unusual queries
- Bot detection

## Resource Planning

### Team Composition
If I were scaling this up, I'd want:
- 2 Backend devs (Python/Flask)
- 1 ML engineer for the query/ranking stuff
- 1 Frontend dev (probably React)
- 1 DevOps (part-time should be enough)
- 1 Product manager

### Infrastructure
Best guess on costs:
- Dev environment: ~$500-800/month depending on testing volume
- Production: $2-5K/month at scale
- API costs: ~$0.50-1 per complex session (could optimize a lot)
- Proxies/rotation: ~$2K/month at scale

### Technical Debt Considerations
Things I'd want to stay on top of:
- Comprehensive refactoring after v2
- Weekly selector maintenance (Amazon keeps changing things)
- Monitoring for detection/blocking
- Regular retraining for the ranking models

## V2 Agent Architecture

The new agent architecture is a big step up from v1:

### Multi-Step Planning
Now it breaks shopping requests into logical steps:
1. Analyze the query to extract all constraints
2. Figure out the best search strategy
3. Apply Amazon's native filters
4. Add custom filtering beyond Amazon's capabilities
5. Research the top candidates deeply
6. Compare products meaningfully
7. Personalize ranking based on preferences

### Reasoning and Decision-Making
- Each step includes justification
- Maintains multiple interpretations for ambiguous queries
- Uses confidence scoring for recommendations

### Context Maintenance
- Stores user preferences
- Remembers conversation history
- Tracks category-specific attributes
- Remembers search refinements

### Personalization System
- Extracts preferences from interactions
- Uses different models by category
- Weights explicit vs. implicit preferences
- Handles new users with reasonable defaults

## Evaluation & Testing

### Current Testing Approach
I've implemented:
- Unit tests for most components
- Integration tests for main workflows
- A/B testing for ranking
- Regression tests for selectors
- Performance benchmarks

### Helpfulness Metrics
Key metrics I'm tracking:
- Success rate (satisfactory results)
- Decision quality vs. expert shoppers
- Time saved vs. manual shopping (this is huge)
- Session completion rates

### User Feedback Methods
- Simple star ratings
- A/B testing
- Tracking refinement requests
- Session recording (with consent)
- Follow-up surveys

### Automated Testing
- Daily selector validation
- Synthetic query generation
- Performance monitoring
- Component error tracking

## Key Challenges & Solutions

### Dynamic Layout
**Solution**: Multiple fallback selectors in priority order

### Detection Risk
**Solution**: Human-like patterns, session rotation, distributed traffic

### Advanced Filtering Beyond Amazon's UI
**Solution**: Rich parameter extraction with post-filtering

### Ambiguous Queries
**Solution**: Conservative parsing with fallbacks and suggestions

### Scaling Challenges
- Serverless architecture for spikes
- Browser instance pooling
- Multi-level caching
- Request queuing
- Regional deployment

## Future Improvements

### Additional Features
- Price history and alerts
- Deal hunting (Black Friday optimization)
- Cross-site price comparison
- Barcode/image search
- Voice interface

### Product Understanding
- Category-specific attributes
- Custom embeddings
- Comparison tables
- Expert knowledge integration

### Performance Optimizations
- Pre-warming browser sessions
- Progressive loading
- Distributed scraping
- Predictive caching

## Conclusion & Next Steps

The v2 system is working well and represents a big step forward from simple search assistance to a genuinely intelligent shopping agent. The deep product understanding, comparison capabilities, and personalization really set it apart.

I'm focusing next on:
1. Finishing unit tests for v2 components
2. Improving error recovery for UI changes
3. Implementing session pooling for better throughput
4. Adding synthetic analysis for limited-review products
5. Building out basic preference tracking

This architecture should support all the future enhancements, with reliability, performance, and personalization as the key areas to develop further.