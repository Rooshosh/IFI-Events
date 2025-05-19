> **Note:** Outdated and AI Generated 🤦

# IFI Events

A Python application that aggregates and displays events from various UiO IFI (Department of Informatics) sources.

~~📋 Project Management Board~~ - Moved to private

## Features

- Event scraping from multiple sources:
  - Peoply.app - Events from student organizations
  - Navet (ifinavet.no) - Company presentations and career events
- Automatic deduplication of events
- FastAPI-based REST API
- Timezone-aware event handling
- PostgreSQL database with Supabase

## Quick Start

### Local Development

1. Set up environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Set up environment variables:
   ```bash
   # Copy template and fill in your Supabase details
   cp .env.template .env
   ```

3. Run in development mode (with auto-reload):
   ```bash
   uvicorn src.api.main:app --reload --port 8000
   ```

4. Run in production mode (without auto-reload):
   ```bash
   uvicorn src.api.main:app --host 0.0.0.0 --port 8000
   ```

### Railway.app Deployment

The application is configured for automatic deployment on Railway.app:

1. Push your code to GitHub
2. Connect your GitHub repository to Railway.app
3. Set up environment variables in Railway.app dashboard:
   ```
   ENVIRONMENT=production
   DATABASE_URL=your_supabase_url
   ```
4. Railway.app will automatically:
   - Detect the Python project
   - Install dependencies from `requirements.txt`
   - Use the `railway.toml` configuration
   - Set up environment variables
   - Deploy your application

### Environment Variables

- `ENVIRONMENT`: Set to 'development' or 'production' (default: 'development')
- `PORT`: Port to run the server on (default: 8000)
- `DATABASE_URL`: PostgreSQL connection URL (required in production)

## API Documentation

When running in development mode, you can access:
- Interactive API docs (Swagger UI): http://localhost:8000/docs
- Alternative API docs (ReDoc): http://localhost:8000/redoc

These are automatically disabled in production for security.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Components

The project consists of several key components:

- **Event Scrapers**: Modules for fetching events from different sources (using BeautifulSoup4 and Requests)
- **FastAPI Backend**: REST API for serving event data
- **CLI Tools**: Command-line tools for managing events and system maintenance
- **Storage**: PostgreSQL database hosted on Supabase

## Documentation

- Each Python module contains detailed documentation in its docstrings
- For CLI tools, use the `--help` flag (e.g., `python scripts/events.py --help`)

## Development

### Database Operations

The project uses SQLAlchemy ORM with PostgreSQL:

- Event data model is defined in `src/models/event.py`
- Database configuration is in `src/db/base.py`
- During development, the database schema is managed through migrations
- See docstrings in the code for detailed usage examples

### Adding a New Event Source

1. Create a new scraper in `src/scrapers/` that inherits from `BaseScraper`
2. Implement the required methods
3. Add the scraper to the list in `scripts/events.py`

### Production Configuration

The application uses environment variables to configure different environments:

- Development mode (default):
  - Interactive API docs enabled
  - SQLite database
  - CORS allows all origins
  - Detailed error responses

- Production mode:
  - API docs disabled
  - PostgreSQL database (requires DATABASE_URL)
  - CORS restricted to specific domains
  - Limited error information for security

To switch between modes, set the ENVIRONMENT variable:
```bash
# Development mode
ENVIRONMENT=development

# Production mode
ENVIRONMENT=production
DATABASE_URL=your_postgresql_url
```

## Running the Application

### Development Mode
```bash
uvicorn src.api.main:app --reload --port 8000
```

### Production Mode
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Environment Variables
- `ENVIRONMENT`: Set to 'development' or 'production' (default: 'development')
- `PORT`: Port to run the server on (default: 8000)
- `WORKERS`: Number of worker processes (default: 1)
- `DATABASE_URL`: PostgreSQL connection URL (required in production) 
