# Amazon Shopping Assistant

This project implements an AI agent that helps with shopping on Amazon using natural language.

## Development Plan Before Input From Lewis

My dev plan rn is:

1. Browser automation - get Playwright or Selenium or Web Scraping working with Amazon
2. Add search and filters - handle specific product queries
3. Product data extraction - scrape prices, reviews, shipping
4. Query parsing - convert user text to search params
5. Basic comparison - rank products by relevance to query
6. Simple conversation - handle follow-ups and refinements

## Project Structure

```
amazon-shopping-assistant/
├── agent/              # core components
├── config/             # settings
├── tests/              # basic tests
├── main.py             # entry point
└── README.md           # this file
```

## Running

```
python main.py
```

Just run the main script and type in shopping queries like "find a coffee maker under $100 with good reviews".
Come up with a bunch of other queries to test.

## TODO

- Create devdoc and update as I go
- Add product extraction
- Connect to OpenAI for query parsing
- Handle rate limits
- Better error handling later