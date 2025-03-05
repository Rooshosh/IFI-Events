> **Note:** Outdated and AI Generated 🤦

# IFI Events

A Python application that aggregates and displays events from various UiO IFI (Department of Informatics) sources.

[📋 Project Management Board](https://leaf-brazil-6c0.notion.site/1a188d83e8eb80b7bd63fa440a92cd48?v=1a188d83e8eb8106b59c000c65789543&pvs=4)

## Features

- Event scraping from multiple sources:
  - Peoply.app - Events from student organizations
  - Navet (ifinavet.no) - Company presentations and career events
- Smart caching system for efficient data retrieval
- Automatic deduplication of events
- Web interface to view upcoming events
- Timezone-aware event handling
- PostgreSQL database with Supabase

## Components

The project consists of several key components:

- **Event Scrapers**: Modules for fetching events from different sources (using BeautifulSoup4 and Requests)
- **Web Interface**: Flask-based web application for viewing events
- **CLI Tools**: Command-line tools for managing events and system maintenance
- **Storage**: PostgreSQL database hosted on Supabase
- **Test Suite**: Comprehensive tests for all components

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

3. Run in development mode:
   ```bash
   FLASK_ENV=development python run.py
   ```

4. Run tests:
   ```bash
   python -m unittest discover tests
   ```

### Replit Deployment

The application is configured to run on Replit:

1. Fork the repository on Replit
2. Add your Supabase credentials in Replit Secrets
3. Choose deployment mode in `.replit`:
   ```toml
   # For development:
   run = "FLASK_ENV=development python run.py"
   # For production:
   # run = "python run.py"
   ```

## Documentation

- Each Python module contains detailed documentation in its docstrings
- For CLI tools, use the `--help` flag (e.g., `python scripts/events.py --help`)
- The web interface includes inline help and tooltips

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
4. Add appropriate tests

### Production Configuration

The application uses environment variables to configure different environments:

- `FLASK_ENV=development`: 
  - Enables debug mode
  - Uses localhost
  - Shows detailed error pages
- `FLASK_ENV` not set (production):
  - Disables debug mode
  - Uses 0.0.0.0
  - Production-ready error handling

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 