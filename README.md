# AI Email Assistant

An AI-powered email assistant system that analyzes email patterns, understands writing styles, and generates contextual email responses using RAG (Retrieval-Augmented Generation) technology.

## Features

- 🔐 Google OAuth 2.0 authentication with Gmail API integration
- 📧 Intelligent email fetching and analysis
- 👥 Client relationship mapping and categorization
- ✍️ Writing style analysis and pattern recognition
- 🤖 AI-powered response generation using RAG
- 🗃️ Vector database storage for semantic search
- 📊 Comprehensive analytics and monitoring

## Technology Stack

- **Backend**: FastAPI, Python 3.11+, SQLAlchemy, Pydantic
- **Database**: PostgreSQL, Redis, ChromaDB (Vector DB)
- **AI/ML**: OpenAI GPT-4, Sentence Transformers, LangChain, spaCy
- **Infrastructure**: Docker, Celery, nginx

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Google Cloud Console project with Gmail API enabled
- OpenAI API key

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd ai-email-assistant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your credentials:
# - GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
# - OPENAI_API_KEY
# - DATABASE_URL (if not using Docker)
# - SECRET_KEY (generate a secure random key)
```

### 3. Run with Docker (Recommended)

```bash
# Start all services
docker-compose -f docker/docker-compose.yml up -d

# Check logs
docker-compose -f docker/docker-compose.yml logs -f backend
```

### 4. Run Locally (Development)

```bash
# Start database services
docker-compose -f docker/docker-compose.yml up postgres redis chroma -d

# Run the application
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Documentation

Once running, visit:
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Project Structure

```
ai-email-assistant/
├── src/
│   ├── config/          # Configuration management
│   ├── models/          # Database models
│   ├── services/        # Business logic services
│   ├── api/             # FastAPI routes
│   ├── utils/           # Utility functions
│   └── tests/           # Test files
├── docker/              # Docker configuration
├── scripts/             # Setup scripts
└── docs/                # Documentation
```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest src/tests/test_main.py

# Run with coverage
pytest --cov=src tests/
```

### Database Management

```bash
# Create database tables
python -c "from src.config.database import create_tables; import asyncio; asyncio.run(create_tables())"

# Run database migrations (when implemented)
alembic upgrade head
```

### Code Quality

```bash
# Format code
black src/

# Check linting
flake8 src/

# Type checking
mypy src/
```

## Current Implementation Status

✅ **Phase 1: Foundation Setup** (Complete)
- Project structure and configuration
- Database models and FastAPI application
- Docker containerization
- Basic API endpoints

✅ **Phase 2: Authentication & Google Integration** (Complete)
- Google OAuth 2.0 service
- Authentication API routes
- Gmail API integration framework

✅ **Phase 3: Email Analysis Engine** (Complete)
- Email fetching service with Gmail API
- Client relationship analysis and categorization
- Writing style analysis with NLP
- Topic extraction and business categorization
- Advanced text processing utilities
- Comprehensive analysis API endpoints

✅ **Phase 4: Vector Database & RAG** (Complete)
- ChromaDB vector database integration
- Advanced email chunking and embedding system
- RAG engine with LangChain integration
- Semantic search capabilities
- Context-aware response generation
- Multi-collection vector storage

🚧 **Phase 5: AI Response Generation** (In Progress)
- RAG-powered response generation (implemented)
- Context-aware email responses (implemented)
- Rule-based templates (planned)
- Response quality validation (planned)

⏳ **Phase 6: Testing & Deployment** (Planned)
- Comprehensive testing
- Production deployment
- Performance optimization

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## Security

- All sensitive data is encrypted
- OAuth 2.0 with Google Workspace
- JWT token management
- GDPR compliance ready
- Regular security audits

## License

This project is proprietary software. All rights reserved.

## Support

For questions and support, please refer to the project documentation or contact the development team.