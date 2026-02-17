# Ethiopian Financial News Aggregation System

A comprehensive system for aggregating, filtering, and querying financial news from Ethiopian sources (Addis Fortune, Capital Ethiopia) and international sources (Reuters) with a focus on treasury bills, capital markets, macroeconomics, and politics.

## Architecture

The system follows Clean Architecture principles with four distinct layers:

- **Domain Layer**: Core business entities and interfaces
- **Use Case Layer**: Business logic orchestration
- **Interface Adapter Layer**: Scrapers and repositories
- **Infrastructure Layer**: FastAPI, MongoDB, Playwright, HTTPX

## Features

- **Multi-Source Scraping**: Automated scraping from Addis Fortune, Capital Ethiopia, and Reuters
- **Intelligent Filtering**: FlashText-based keyword extraction for financial relevance
- **RESTful API**: FastAPI-based API with comprehensive query capabilities
- **Scheduled Harvesting**: Automatic news harvesting every 30 minutes with weekly deep archive
- **Legal Compliance**: Respects robots.txt and implements rate limiting
- **Cloudflare Bypass**: Playwright with stealth mode for Reuters scraping

## Prerequisites

- Python 3.10+
- MongoDB 7.0+
- Docker and Docker Compose (for containerized deployment)

## Installation

### Local Development

1. Clone the repository:
```bash
cd NewsAggregationSystem
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers:
```bash
playwright install chromium
```

5. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

6. Start MongoDB (if not using Docker):
```bash
# Using Docker
docker run -d -p 27017:27017 --name mongodb mongo:7.0
```

7. Run the application:
```bash
uvicorn src.api.main:app --reload
```

### Docker Deployment

1. Build and start all services:
```bash
docker-compose up -d
```

2. View logs:
```bash
docker-compose logs -f api
```

3. Stop services:
```bash
docker-compose down
```

## Configuration

Environment variables (see `.env.example`):

- `MONGODB_URL`: MongoDB connection string
- `MONGODB_DB_NAME`: Database name
- `API_HOST`: API host (default: 0.0.0.0)
- `API_PORT`: API port (default: 8000)
- `RATE_LIMIT_DELAY`: Delay between requests in seconds (default: 5)
- `CIRCUIT_BREAKER_THRESHOLD`: Errors before disabling source (default: 5)
- `CIRCUIT_BREAKER_TIMEOUT`: Circuit breaker timeout in seconds (default: 3600)
- `USER_AGENT`: User agent string for scrapers
- `LOG_LEVEL`: Logging level (default: INFO)

## API Usage

### Get News Articles

```bash
# Get all news
GET /api/v1/news

# Filter by category
GET /api/v1/news?category=Treasury+Bills

# Filter by source
GET /api/v1/news?source=Reuters

# Full-text search
GET /api/v1/news?q=ESX

# Date range
GET /api/v1/news?start_date=2025-01-01T00:00:00&end_date=2025-01-31T23:59:59

# Pagination
GET /api/v1/news?limit=20&skip=0

# Combined filters
GET /api/v1/news?category=Capital+Markets&source=Addis+Fortune&limit=10
```

### Manual Harvest

```bash
POST /api/v1/harvest
```

### API Documentation

Interactive API documentation available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Financial Taxonomy

The system filters articles using the following categories:

- **Treasury Bills**: T-Bills, auctions, yields, NBE
- **Capital Markets**: ESX, IPO, stocks, trading, Brook Taye
- **Macroeconomics**: Inflation, GDP, exchange rates, IMF, World Bank
- **Politics**: Proclamations, Parliament, regulations, government policy

## Scheduled Jobs

- **Quick Harvest**: Runs every 30 minutes, fetches 10 articles per source
- **Deep Archive**: Runs weekly on Sunday at 2 AM, fetches 50 articles per source

## Database Access

Mongo Express web UI available at http://localhost:8081 (admin/admin)

## Development

### Project Structure

```
src/
├── domain/           # Core entities and interfaces
├── use_cases/        # Business logic
├── adapters/         # Scrapers and repositories
├── infrastructure/   # Database, NLP, config
└── api/             # FastAPI application
```

### Running Tests

```bash
pytest tests/
```

## Legal Compliance

The system implements:

- robots.txt compliance
- Rate limiting (5-10 seconds between requests)
- Circuit breaker pattern (disables source after 5 consecutive errors)
- Ethical scraping practices
- Compliance with Ethiopian Computer Crime Proclamation No. 958/2016

## Troubleshooting

### Playwright Issues

If Playwright fails to install browsers:
```bash
playwright install chromium
playwright install-deps chromium
```

### MongoDB Connection Issues

Ensure MongoDB is running and accessible:
```bash
docker-compose ps mongodb
```

### Scraping Failures

Check logs for circuit breaker activations:
```bash
docker-compose logs api | grep "Circuit breaker"
```

## License

This project is for educational and research purposes.

## Contributing

Contributions are welcome! Please ensure code follows Clean Architecture principles and includes appropriate error handling and logging.

