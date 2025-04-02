# Amazon Shopping Assistant - Design Doc

## Overview

This doc outlines the approach for the Amazon Shopping Assistant. Started with v0 implementation and added v1 enhancements.

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
Converts natural language to structured params using regex. Extracts product type, price range, ratings, etc.

### ProductAnalyzer
Ranks products using weighted scoring based on ratings, reviews, price, etc. v1 adds better relevance scoring and improved recommendation explanations.

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
Using regex to extract:
- Product type
- Price range
- Rating requirements
- Prime preference
- Keywords

### Ranking Algorithm
Weighted scoring:
- Rating (30%)
- Reviews (20%)
- Price (20%)
- Prime (10%)
- Relevance (20%)

## Version Roadmap

### v0 (original)
- Basic filters
- Regex parsing
- Simple scoring
- Basic conversation

### v1 (current)
- Fixed product extraction with multiple selectors
- Enhanced scoring system with better relevance matching
- Improved recommendation explanations
- Follow-up detection and context tracking
- Better response formatting and suggestions

### v2 (future)
- AI-powered query understanding
- Planning and multi-step workflows
- User preference learning
- Proactive refinements
- Comparative analysis

## v1 Implementation Notes

Fixed critical issues:
1. Solved "Unknown Title" bug with multiple fallback selectors in AmazonNavigator
2. Enhanced ProductAnalyzer with better scoring that considers more factors
3. Added follow-up detection to ConversationManager for more natural conversations
4. Improved response formatting with contextual suggestions
5. Added support for refining previous searches

These changes maintain the same interfaces as v0 for backward compatibility while significantly improving functionality.

## Challenges & Solutions

### Dynamic Layout
Solution: Multiple fallback selectors for key elements

### Detection Risk
Solution: Human-like behavior, random delays

### Ambiguous Queries
Solution: Conservative parsing with better keyword extraction

## Testing Approach

- Manual CLI testing
- Unit tests for individual components
- Future: regression tests, performance benchmarks

## Next Steps

1. Complete unit tests 
2. Add error recovery for common failures as Lewis said
3. Add AI-based query parsing for v2
4. Implement product comparison feature
5. Give user warning about the robot checker