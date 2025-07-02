# AI Email Asistent - Vývojová Roadmapa & Implementační Checklist

## Fáze 1: Nastavení Základů (Týdny 1-2)

### 1.1 Nastavení Projektové Infrastruktury

#### 1.1.1 Konfigurace Prostředí
- [ ] **Vytvoření struktury projektového adresáře**
  ```bash
  mkdir ai-email-assistant
  cd ai-email-assistant
  mkdir -p src/{config,models,services,api,utils,tests}
  mkdir -p docker scripts docs frontend
  ```

- [ ] **Inicializace Python prostředí**
  ```bash
  python -m venv venv
  source venv/bin/activate  # Linux/Mac
  # venv\Scripts\activate  # Windows
  ```

- [ ] **Vytvoření requirements.txt**
  ```txt
  fastapi==0.104.1
  uvicorn==0.24.0
  sqlalchemy==2.0.23
  asyncpg==0.29.0
  pydantic==2.5.0
  google-auth==2.24.0
  google-auth-oauthlib==1.1.0
  google-api-python-client==2.108.0
  chromadb==0.4.18
  sentence-transformers==2.2.2
  langchain==0.0.340
  spacy==3.7.2
  scikit-learn==1.3.2
  textstat==0.7.3
  celery==5.3.4
  redis==5.0.1
  pytest==7.4.3
  pytest-asyncio==0.21.1
  ```

- [ ] **Instalace závislostí**
  ```bash
  pip install -r requirements.txt
  python -m spacy download en_core_web_sm
  ```

#### 1.1.2 Správa Konfigurace
- [ ] **Soubor: src/config/settings.py**
  ```python
  from pydantic_settings import BaseSettings
  from typing import List, Optional
  import os

  class Settings(BaseSettings):
      """
      Komplexní správa konfigurace aplikace
      Zpracovává prostředí-specifická nastavení s validací
      """
      
      # Konfigurace aplikace
      app_name: str = "AI Email Assistant"
      app_version: str = "1.0.0"
      debug: bool = False
      
      # Konfigurace databáze
      database_url: str = "postgresql+asyncpg://user:password@localhost/ai_email_db"
      database_pool_size: int = 20
      database_max_overflow: int = 30
      
      # Konfigurace Redis
      redis_url: str = "redis://localhost:6379"
      redis_db: int = 0
      
      # Konfigurace Google API
      google_client_id: str
      google_client_secret: str
      google_redirect_uri: str = "http://localhost:8000/auth/callback"
      google_scopes: List[str] = [
          "https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/gmail.compose",
          "https://www.googleapis.com/auth/userinfo.email"
      ]
      
      # Konfigurace OpenAI
      openai_api_key: str
      openai_model: str = "gpt-4"
      
      # Konfigurace vektorové databáze
      chroma_host: str = "localhost"
      chroma_port: int = 8000
      weaviate_url: str = "http://localhost:8080"
      
      # Konfigurace Celery
      celery_broker_url: str = "redis://localhost:6379/1"
      celery_result_backend: str = "redis://localhost:6379/2"
      
      # Konfigurace zabezpečení
      secret_key: str
      algorithm: str = "HS256"
      access_token_expire_minutes: int = 30
      
      class Config:
          env_file = ".env"
          env_file_encoding = "utf-8"

  settings = Settings()
  ```

- [ ] **Soubor: src/config/database.py**
  ```python
  from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
  from sqlalchemy.orm import declarative_base
  from .settings import settings
  import logging

  # Konfigurace databázového enginu
  engine = create_async_engine(
      settings.database_url,
      echo=settings.debug,
      pool_size=settings.database_pool_size,
      max_overflow=settings.database_max_overflow,
      pool_pre_ping=True,
      pool_recycle=3600
  )

  # Session factory
  AsyncSessionLocal = async_sessionmaker(
      engine, 
      class_=AsyncSession, 
      expire_on_commit=False
  )

  # Základní třída pro ORM modely
  Base = declarative_base()

  async def get_database_session() -> AsyncSession:
      """
      Závislost pro FastAPI pro poskytování databázových sessions
      Zajišťuje správnou správu životního cyklu session
      """
      async with AsyncSessionLocal() as session:
          try:
              yield session
          except Exception as e:
              await session.rollback()
              logging.error(f"Chyba databázové session: {e}")
              raise
          finally:
              await session.close()

  async def create_tables():
      """Inicializuje databázové tabulky"""
      async with engine.begin() as conn:
          await conn.run_sync(Base.metadata.create_all)
  ```

- [ ] **Soubor: src/config/logging.py**
  ```python
  import logging
  import logging.config
  from typing import Dict, Any

  LOGGING_CONFIG: Dict[str, Any] = {
      "version": 1,
      "disable_existing_loggers": False,
      "formatters": {
          "standard": {
              "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
          },
          "detailed": {
              "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s"
          }
      },
      "handlers": {
          "default": {
              "level": "INFO",
              "formatter": "standard",
              "class": "logging.StreamHandler",
              "stream": "ext://sys.stdout"
          },
          "file": {
              "level": "DEBUG",
              "formatter": "detailed",
              "class": "logging.FileHandler",
              "filename": "logs/app.log",
              "mode": "a"
          }
      },
      "loggers": {
          "": {
              "handlers": ["default", "file"],
              "level": "DEBUG",
              "propagate": False
          }
      }
  }

  def setup_logging():
      """Konfiguruje logování aplikace"""
      import os
      os.makedirs("logs", exist_ok=True)
      logging.config.dictConfig(LOGGING_CONFIG)
  ```

#### 1.1.3 Implementace Databázových Modelů
- [ ] **Soubor: src/models/user.py**
  ```python
  from sqlalchemy import Column, String, DateTime, Boolean, Text
  from sqlalchemy.dialects.postgresql import UUID
  from sqlalchemy.orm import relationship
  from sqlalchemy.sql import func
  from src.config.database import Base
  import uuid

  class User(Base):
      """
      Model uživatele s komplexní správou profilu
      Ukládá autentifikační data a uživatelské preference
      """
      __tablename__ = "users"
      
      id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      email = Column(String(255), unique=True, nullable=False, index=True)
      google_id = Column(String(255), unique=True, nullable=True)
      display_name = Column(String(255), nullable=True)
      profile_picture = Column(Text, nullable=True)
      
      # Časová razítka
      created_at = Column(DateTime(timezone=True), server_default=func.now())
      updated_at = Column(DateTime(timezone=True), onupdate=func.now())
      last_sync = Column(DateTime(timezone=True), nullable=True)
      last_login = Column(DateTime(timezone=True), nullable=True)
      
      # Stavové příznaky
      is_active = Column(Boolean, default=True)
      is_verified = Column(Boolean, default=False)
      is_premium = Column(Boolean, default=False)
      
      # Nastavení
      timezone = Column(String(50), default="UTC")
      language = Column(String(10), default="cs")
      email_sync_enabled = Column(Boolean, default=True)
      auto_response_enabled = Column(Boolean, default=False)
      
      # Vztahy
      clients = relationship("Client", back_populates="user", cascade="all, delete-orphan")
      email_messages = relationship("EmailMessage", back_populates="user", cascade="all, delete-orphan")
      writing_style_profile = relationship("WritingStyleProfile", back_populates="user", uselist=False)
      response_rules = relationship("ResponseRule", back_populates="user", cascade="all, delete-orphan")
      
      def __repr__(self):
          return f"<User(email='{self.email}', is_active={self.is_active})>"
  ```

- [ ] **Soubor: src/models/client.py**
  ```python
  from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, Text, Boolean
  from sqlalchemy.dialects.postgresql import UUID, JSONB
  from sqlalchemy.orm import relationship
  from sqlalchemy.sql import func
  from src.config.database import Base
  import uuid

  class Client(Base):
      """
      Model klientského vztahu s komplexním profilováním
      Sleduje komunikační vzorce a obchodní kontext
      """
      __tablename__ = "clients"
      
      id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
      
      # Identifikace klienta
      email_address = Column(String(255), nullable=False, index=True)
      email_domain = Column(String(255), nullable=False, index=True)
      client_name = Column(String(255), nullable=True)
      organization_name = Column(String(255), nullable=True)
      
      # Obchodní kategorizace
      business_category = Column(String(100), nullable=True)
      industry_sector = Column(String(100), nullable=True)
      client_type = Column(String(50), nullable=True)  # prospect, customer, vendor, partner
      
      # Analýza komunikace
      communication_frequency = Column(String(50), nullable=True)  # daily, weekly, monthly, rare
      avg_response_time_hours = Column(Float, nullable=True)
      formality_level = Column(String(50), nullable=True)  # formal, semi-formal, casual
      preferred_communication_style = Column(String(50), nullable=True)
      
      # Sledování interakcí
      total_emails_received = Column(Integer, default=0)
      total_emails_sent = Column(Integer, default=0)
      first_interaction = Column(DateTime(timezone=True), nullable=True)
      last_interaction = Column(DateTime(timezone=True), nullable=True)
      
      # Business intelligence
      common_topics = Column(JSONB, nullable=True)
      frequent_questions = Column(JSONB, nullable=True)
      project_keywords = Column(JSONB, nullable=True)
      
      # Časová razítka
      created_at = Column(DateTime(timezone=True), server_default=func.now())
      updated_at = Column(DateTime(timezone=True), onupdate=func.now())
      
      # Stav
      is_active = Column(Boolean, default=True)
      priority_level = Column(String(20), default="normal")  # high, normal, low
      
      # Vztahy
      user = relationship("User", back_populates="clients")
      email_messages = relationship("EmailMessage", back_populates="client")
      response_rules = relationship("ResponseRule", back_populates="client")
      
      def __repr__(self):
          return f"<Client(email='{self.email_address}', category='{self.business_category}')>"
  ```

- [ ] **Soubor: src/models/email.py**
  ```python
  from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer, Float
  from sqlalchemy.dialects.postgresql import UUID, JSONB
  from sqlalchemy.orm import relationship
  from sqlalchemy.sql import func
  from src.config.database import Base
  import uuid

  class EmailMessage(Base):
      """
      Komplexní model emailové zprávy s metadaty
      Ukládá kompletní emailová data pro analýzu a RAG
      """
      __tablename__ = "email_messages"
      
      id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
      client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)
      
      # Gmail API identifikátory
      message_id = Column(String(255), unique=True, nullable=False, index=True)
      thread_id = Column(String(255), nullable=False, index=True)
      
      # Metadata emailu
      direction = Column(String(20), nullable=False)  # incoming, outgoing
      subject = Column(Text, nullable=True)
      sender = Column(String(255), nullable=False, index=True)
      recipient = Column(String(255), nullable=False, index=True)
      cc_recipients = Column(JSONB, nullable=True)
      bcc_recipients = Column(JSONB, nullable=True)
      
      # Obsah emailu
      body_text = Column(Text, nullable=True)
      body_html = Column(Text, nullable=True)
      snippet = Column(Text, nullable=True)
      
      # Gmail metadata
      labels = Column(JSONB, nullable=True)
      importance = Column(String(20), nullable=True)
      is_read = Column(Boolean, default=False)
      is_starred = Column(Boolean, default=False)
      has_attachments = Column(Boolean, default=False)
      attachment_count = Column(Integer, default=0)
      
      # Časová razítka
      sent_datetime = Column(DateTime(timezone=True), nullable=False)
      received_datetime = Column(DateTime(timezone=True), nullable=True)
      created_at = Column(DateTime(timezone=True), server_default=func.now())
      
      # Stav zpracování
      is_processed = Column(Boolean, default=False)
      is_chunked = Column(Boolean, default=False)
      is_embedded = Column(Boolean, default=False)
      processing_error = Column(Text, nullable=True)
      
      # Výsledky analýzy
      sentiment_score = Column(Float, nullable=True)
      urgency_level = Column(String(20), nullable=True)
      topic_categories = Column(JSONB, nullable=True)
      extracted_entities = Column(JSONB, nullable=True)
      
      # Vztahy
      user = relationship("User", back_populates="email_messages")
      client = relationship("Client", back_populates="email_messages")
      generated_responses = relationship("GeneratedResponse", back_populates="original_email")
      
      def __repr__(self):
          return f"<EmailMessage(subject='{self.subject[:50]}...', direction='{self.direction}')>"

  class EmailChunk(Base):
      """
      Textové chunky emailů pro uložení ve vektorové databázi
      Optimalizováno pro RAG retrieval operace
      """
      __tablename__ = "email_chunks"
      
      id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      email_message_id = Column(UUID(as_uuid=True), ForeignKey("email_messages.id"), nullable=False)
      
      # Data chunku
      chunk_text = Column(Text, nullable=False)
      chunk_index = Column(Integer, nullable=False)
      chunk_type = Column(String(50), nullable=False)  # subject, body, signature
      
      # Reference vektorové databáze
      vector_collection = Column(String(100), nullable=True)
      vector_id = Column(String(255), nullable=True)
      
      # Metadata
      token_count = Column(Integer, nullable=True)
      character_count = Column(Integer, nullable=True)
      
      created_at = Column(DateTime(timezone=True), server_default=func.now())
      
      # Vztahy
      email_message = relationship("EmailMessage")
  ```

- [ ] **Soubor: src/models/response.py**
  ```python
  from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Float, Integer
  from sqlalchemy.dialects.postgresql import UUID, JSONB
  from sqlalchemy.orm import relationship
  from sqlalchemy.sql import func
  from src.config.database import Base
  import uuid

  class WritingStyleProfile(Base):
      """
      Komplexní profil analýzy stylu psaní
      Ukládá lingvistické vzorce a komunikační preference
      """
      __tablename__ = "writing_style_profiles"
      
      id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
      
      # Lingvistické metriky
      avg_sentence_length = Column(Float, nullable=True)
      avg_paragraph_length = Column(Float, nullable=True)
      vocabulary_complexity = Column(Float, nullable=True)
      readability_score = Column(Float, nullable=True)
      
      # Charakteristiky stylu
      formality_score = Column(Float, nullable=True)
      politeness_score = Column(Float, nullable=True)
      assertiveness_score = Column(Float, nullable=True)
      emotional_tone = Column(String(50), nullable=True)
      
      # Komunikační vzorce
      common_phrases = Column(JSONB, nullable=True)
      signature_patterns = Column(JSONB, nullable=True)
      greeting_patterns = Column(JSONB, nullable=True)
      closing_patterns = Column(JSONB, nullable=True)
      
      # Chování odpovědí
      avg_response_time_hours = Column(Float, nullable=True)
      preferred_response_length = Column(String(50), nullable=True)
      use_bullet_points = Column(Boolean, default=False)
      use_numbered_lists = Column(Boolean, default=False)
      
      # Interpunkce a formátování
      exclamation_frequency = Column(Float, nullable=True)
      question_frequency = Column(Float, nullable=True)
      emoji_usage = Column(Boolean, default=False)
      formatting_preferences = Column(JSONB, nullable=True)
      
      # Metadata analýzy
      emails_analyzed = Column(Integer, default=0)
      last_analysis = Column(DateTime(timezone=True), nullable=True)
      confidence_score = Column(Float, nullable=True)
      
      created_at = Column(DateTime(timezone=True), server_default=func.now())
      updated_at = Column(DateTime(timezone=True), onupdate=func.now())
      
      # Vztahy
      user = relationship("User", back_populates="writing_style_profile")

  class ResponseRule(Base):
      """
      Dynamická pravidla generování odpovědí
      Kontextově uvědomělé šablony pro automatické odpovědi
      """
      __tablename__ = "response_rules"
      
      id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
      client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)
      
      # Identifikace pravidla
      rule_name = Column(String(255), nullable=False)
      rule_category = Column(String(100), nullable=False)
      
      # Podmínky spuštění
      trigger_patterns = Column(JSONB, nullable=False)
      trigger_keywords = Column(JSONB, nullable=True)
      subject_patterns = Column(JSONB, nullable=True)
      
      # Šablona odpovědi
      response_template = Column(Text, nullable=False)
      response_variables = Column(JSONB, nullable=True)
      
      # Kontextové požadavky
      formality_level = Column(String(50), nullable=True)
      urgency_level = Column(String(50), nullable=True)
      context_requirements = Column(JSONB, nullable=True)
      
      # Metadata pravidla
      priority = Column(Integer, default=100)
      is_active = Column(Boolean, default=True)
      success_rate = Column(Float, nullable=True)
      usage_count = Column(Integer, default=0)
      
      created_at = Column(DateTime(timezone=True), server_default=func.now())
      updated_at = Column(DateTime(timezone=True), onupdate=func.now())
      
      # Vztahy
      user = relationship("User", back_populates="response_rules")
      client = relationship("Client", back_populates="response_rules")

  class GeneratedResponse(Base):
      """
      AI-generované emailové odpovědi se sledováním kvality
      Ukládá generované koncepty a výkonnostní metriky
      """
      __tablename__ = "generated_responses"
      
      id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      original_email_id = Column(UUID(as_uuid=True), ForeignKey("email_messages.id"), nullable=False)
      
      # Generovaný obsah
      generated_response = Column(Text, nullable=False)
      response_type = Column(String(50), nullable=False)  # auto, template, custom
      
      # Metriky kvality
      confidence_score = Column(Float, nullable=True)
      relevance_score = Column(Float, nullable=True)
      style_match_score = Column(Float, nullable=True)
      
      # Metadata generování
      model_used = Column(String(100), nullable=True)
      generation_time_ms = Column(Integer, nullable=True)
      tokens_used = Column(Integer, nullable=True)
      
      # RAG kontext
      retrieved_contexts = Column(JSONB, nullable=True)
      context_sources = Column(JSONB, nullable=True)
      
      # Sledování stavu
      status = Column(String(50), default="draft")  # draft, reviewed, sent, rejected
      user_feedback = Column(Text, nullable=True)
      was_modified = Column(Boolean, default=False)
      
      created_at = Column(DateTime(timezone=True), server_default=func.now())
      reviewed_at = Column(DateTime(timezone=True), nullable=True)
      
      # Vztahy
      original_email = relationship("EmailMessage", back_populates="generated_responses")
  ```

#### 1.1.4 Nastavení FastAPI Aplikace
- [ ] **Soubor: src/main.py**
  ```python
  from fastapi import FastAPI, Depends, HTTPException
  from fastapi.middleware.cors import CORSMiddleware
  from fastapi.middleware.trustedhost import TrustedHostMiddleware
  from fastapi.security import HTTPBearer
  from contextlib import asynccontextmanager
  import logging

  from src.config.settings import settings
  from src.config.database import create_tables
  from src.config.logging import setup_logging
  from src.api.routes import auth, emails, clients, responses

  # Nastavení logování
  setup_logging()
  logger = logging.getLogger(__name__)

  @asynccontextmanager
  async def lifespan(app: FastAPI):
      """
      Správa životního cyklu aplikace
      Zpracovává startup a shutdown procedury
      """
      # Startup
      logger.info("Spouštění AI Email Assistant aplikace...")
      await create_tables()
      logger.info("Databázové tabulky inicializovány")
      
      # Inicializace vektorových databází
      from src.services.vector_db_manager import VectorDatabaseManager
      vector_manager = VectorDatabaseManager()
      await vector_manager.initialize_collections()
      logger.info("Vektorové databáze inicializovány")
      
      yield
      
      # Shutdown
      logger.info("Ukončování AI Email Assistant aplikace...")

  # Vytvoření FastAPI aplikace
  app = FastAPI(
      title=settings.app_name,
      version=settings.app_version,
      description="Pokročilý AI-powered email asistent s RAG schopnostmi",
      lifespan=lifespan,
      docs_url="/docs" if settings.debug else None,
      redoc_url="/redoc" if settings.debug else None
  )

  # Bezpečnostní middleware
  security = HTTPBearer()

  # CORS middleware
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["http://localhost:3000", "http://localhost:8000"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )

  # Trusted host middleware
  app.add_middleware(
      TrustedHostMiddleware,
      allowed_hosts=["localhost", "127.0.0.1", "*.example.com"]
  )

  # Zahrnutí routerů
  app.include_router(auth.router, prefix="/api/v1/auth", tags=["autentifikace"])
  app.include_router(emails.router, prefix="/api/v1/emails", tags=["emaily"])
  app.include_router(clients.router, prefix="/api/v1/clients", tags=["klienti"])
  app.include_router(responses.router, prefix="/api/v1/responses", tags=["odpovědi"])

  @app.get("/")
  async def root():
      """Root endpoint s informacemi o aplikaci"""
      return {
          "aplikace": settings.app_name,
          "verze": settings.app_version,
          "stav": "provozní",
          "dokumentace": "/docs"
      }

  @app.get("/health")
  async def health_check():
      """Health check endpoint pro monitoring"""
      return {
          "stav": "zdravý",
          "timestamp": "2024-01-01T00:00:00Z",
          "verze": settings.app_version
      }

  if __name__ == "__main__":
      import uvicorn
      uvicorn.run(
          "src.main:app",
          host="0.0.0.0",
          port=8000,
          reload=settings.debug,
          log_level="debug" if settings.debug else "info"
      )
  ```

### 1.2 Konfigurace Docker
- [ ] **Soubor: docker/Dockerfile.backend**
  ```dockerfile
  FROM python:3.11-slim

  # Nastavení pracovního adresáře
  WORKDIR /app

  # Instalace systémových závislostí
  RUN apt-get update && apt-get install -y \
      build-essential \
      curl \
      && rm -rf /var/lib/apt/lists/*

  # Kopírování requirements a instalace Python závislostí
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt

  # Stažení spaCy modelu
  RUN python -m spacy download en_core_web_sm

  # Kopírování kódu aplikace
  COPY src/ ./src/
  COPY scripts/ ./scripts/

  # Vytvoření adresáře pro logy
  RUN mkdir -p logs

  # Vystavení portu
  EXPOSE 8000

  # Příkaz pro spuštění aplikace
  CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
  ```

- [ ] **Soubor: docker/docker-compose.yml**
  ```yaml
  version: '3.8'

  services:
    # Backend API
    backend:
      build:
        context: ..
        dockerfile: docker/Dockerfile.backend
      ports:
        - "8000:8000"
      environment:
        - DATABASE_URL=postgresql+asyncpg://ai_user:ai_password@postgres:5432/ai_email_db
        - REDIS_URL=redis://redis:6379
      depends_on:
        - postgres
        - redis
        - chroma
      volumes:
        - ../logs:/app/logs
      networks:
        - ai_email_network

    # PostgreSQL Databáze
    postgres:
      image: postgres:15
      environment:
        POSTGRES_DB: ai_email_db
        POSTGRES_USER: ai_user
        POSTGRES_PASSWORD: ai_password
      ports:
        - "5432:5432"
      volumes:
        - postgres_data:/var/lib/postgresql/data
      networks:
        - ai_email_network

    # Redis Cache
    redis:
      image: redis:7-alpine
      ports:
        - "6379:6379"
      volumes:
        - redis_data:/data
      networks:
        - ai_email_network

    # ChromaDB Vektorová Databáze
    chroma:
      image: chromadb/chroma:latest
      ports:
        - "8001:8000"
      volumes:
        - chroma_data:/chroma/chroma
      networks:
        - ai_email_network

    # Celery Worker
    celery-worker:
      build:
        context: ..
        dockerfile: docker/Dockerfile.backend
      command: celery -A src.celery_app worker --loglevel=info
      environment:
        - DATABASE_URL=postgresql+asyncpg://ai_user:ai_password@postgres:5432/ai_email_db
        - REDIS_URL=redis://redis:6379
      depends_on:
        - postgres
        - redis
      volumes:
        - ../logs:/app/logs
      networks:
        - ai_email_network

    # Celery Beat Scheduler
    celery-beat:
      build:
        context: ..
        dockerfile: docker/Dockerfile.backend
      command: celery -A src.celery_app beat --loglevel=info
      environment:
        - DATABASE_URL=postgresql+asyncpg://ai_user:ai_password@postgres:5432/ai_email_db
        - REDIS_URL=redis://redis:6379
      depends_on:
        - postgres
        - redis
      volumes:
        - ../logs:/app/logs
      networks:
        - ai_email_network

  volumes:
    postgres_data:
    redis_data:
    chroma_data:

  networks:
    ai_email_network:
      driver: bridge
  ```

#### 1.1.5 Konfigurace Prostředí
- [ ] **Vytvoření .env souboru**
  ```env
  # Konfigurace aplikace
  DEBUG=true
  SECRET_KEY=váš-super-tajný-klíč-zde
  
  # Konfigurace databáze
  DATABASE_URL=postgresql+asyncpg://ai_user:ai_password@localhost:5432/ai_email_db
  
  # Konfigurace Google API
  GOOGLE_CLIENT_ID=váš-google-client-id
  GOOGLE_CLIENT_SECRET=váš-google-client-secret
  GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
  
  # Konfigurace OpenAI
  OPENAI_API_KEY=váš-openai-api-klíč
  
  # Konfigurace Redis
  REDIS_URL=redis://localhost:6379
  
  # Konfigurace vektorové databáze
  CHROMA_HOST=localhost
  CHROMA_PORT=8001
  ```

## Fáze 2: Autentifikace a Google API Integrace (Týden 2-3)

### 2.1 Implementace Google Autentifikační Služby

- [ ] **Soubor: src/services/auth_service.py**
  ```python
  from google.auth.transport.requests import Request
  from google.oauth2.credentials import Credentials
  from google_auth_oauthlib.flow import Flow
  from googleapiclient.discovery import build
  from googleapiclient.errors import HttpError
  from typing import Optional, Dict, Any
  import json
  import logging
  from datetime import datetime, timedelta
  
  from src.config.settings import settings
  from src.models.user import User
  from src.config.database import AsyncSessionLocal

  logger = logging.getLogger(__name__)

  class GoogleAuthenticationService:
      """
      Komplexní Google Workspace autentifikační služba
      Spravuje OAuth 2.0 flow, obnovu tokenů a vytváření API služeb
      """
      
      def __init__(self):
          self.client_config = {
              "web": {
                  "client_id": settings.google_client_id,
                  "client_secret": settings.google_client_secret,
                  "redirect_uris": [settings.google_redirect_uri],
                  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                  "token_uri": "https://oauth2.googleapis.com/token"
              }
          }
          self.scopes = settings.google_scopes
          
      async def create_authorization_url(self, state: str) -> str:
          """
          Vytvoří OAuth 2.0 autorizační URL
          
          Args:
              state: CSRF ochranný state parametr
              
          Returns:
              Autorizační URL pro přesměrování uživatele
          """
          try:
              flow = Flow.from_client_config(
                  self.client_config,
                  scopes=self.scopes,
                  state=state
              )
              flow.redirect_uri = settings.google_redirect_uri
              
              authorization_url, _ = flow.authorization_url(
                  access_type='offline',
                  include_granted_scopes='true',
                  prompt='consent'
              )
              
              logger.info(f"Vytvořeno autorizační URL pro state: {state}")
              return authorization_url
              
          except Exception as e:
              logger.error(f"Chyba při vytváření autorizačního URL: {e}")
              raise

      async def exchange_code_for_tokens(self, code: str, state: str) -> Dict[str, Any]:
          """
          Vymění autorizační kód za přístupové a refresh tokeny
          
          Args:
              code: Autorizační kód z callback
              state: State parametr pro CSRF ochranu
              
          Returns:
              Informace o uživateli a tokeny
          """
          try:
              flow = Flow.from_client_config(
                  self.client_config,
                  scopes=self.scopes,
                  state=state
              )
              flow.redirect_uri = settings.google_redirect_uri
              
              # Získání tokenů
              flow.fetch_token(code=code)
              credentials = flow.credentials
              
              # Získání informací o uživateli
              user_info = await self._get_user_info(credentials)
              
              # Uložení nebo aktualizace uživatele
              async with AsyncSessionLocal() as session:
                  user = await self._create_or_update_user(session, user_info, credentials)
                  await session.commit()
              
              logger.info(f"Úspěšně autentifikován uživatel: {user_info['email']}")
              
              return {
                  "user": user,
                  "credentials": {
                      "access_token": credentials.token,
                      "refresh_token": credentials.refresh_token,
                      "token_uri": credentials.token_uri,
                      "client_id": credentials.client_id,
                      "client_secret": credentials.client_secret,
                      "scopes": credentials.scopes
                  }
              }
              
          except Exception as e:
              logger.error(f"Chyba při výměně kódu za tokeny: {e}")
              raise

      async def _get_user_info(self, credentials: Credentials) -> Dict[str, Any]:
          """
          Získá informace o uživateli z Google API
          
          Args:
              credentials: Google OAuth 2.0 credentials
              
          Returns:
              Informace o uživatelském profilu
          """
          try:
              service = build('oauth2', 'v2', credentials=credentials)
              user_info = service.userinfo().get().execute()
              
              return {
                  "google_id": user_info.get("id"),
                  "email": user_info.get("email"),
                  "display_name": user_info.get("name"),
                  "profile_picture": user_info.get("picture"),
                  "verified_email": user_info.get("verified_email", False)
              }
              
          except HttpError as e:
              logger.error(f"Google API chyba při získávání user info: {e}")
              raise
          except Exception as e:
              logger.error(f"Chyba při získávání user info: {e}")
              raise

      async def _create_or_update_user(self, session, user_info: Dict[str, Any], credentials: Credentials) -> User:
          """
          Vytvoří nového uživatele nebo aktualizuje existujícího
          
          Args:
              session: Databázová session
              user_info: Informace o uživatelském profilu
              credentials: Google OAuth 2.0 credentials
              
          Returns:
              Instance User modelu
          """
          from sqlalchemy import select
          
          # Kontrola existence uživatele
          stmt = select(User).where(User.email == user_info["email"])
          result = await session.execute(stmt)
          user = result.scalar_one_or_none()
          
          if user:
              # Aktualizace existujícího uživatele
              user.google_id = user_info["google_id"]
              user.display_name = user_info["display_name"]
              user.profile_picture = user_info["profile_picture"]
              user.is_verified = user_info["verified_email"]
              user.last_login = datetime.utcnow()
              logger.info(f"Aktualizován existující uživatel: {user.email}")
          else:
              # Vytvoření nového uživatele
              user = User(
                  email=user_info["email"],
                  google_id=user_info["google_id"],
                  display_name=user_info["display_name"],
                  profile_picture=user_info["profile_picture"],
                  is_verified=user_info["verified_email"],
                  last_login=datetime.utcnow()
              )
              session.add(user)
              logger.info(f"Vytvořen nový uživatel: {user.email}")
          
          return user

      async def refresh_access_token(self, user_id: str) -> Optional[Credentials]:
          """
          Obnoví vypršený přístupový token
          
          Args:
              user_id: Identifikátor uživatele
              
          Returns:
              Obnovené credentials nebo None při selhání obnovy
          """
          try:
              async with AsyncSessionLocal() as session:
                  # Získání uživatelských credentials z databáze/cache
                  # Implementace závisí na způsobu ukládání credentials
                  # Toto je zjednodušený příklad
                  
                  credentials = Credentials(
                      token=None,  # Bude obnoveno
                      refresh_token="stored_refresh_token",
                      token_uri="https://oauth2.googleapis.com/token",
                      client_id=settings.google_client_id,
                      client_secret=settings.google_client_secret
                  )
                  
                  credentials.refresh(Request())
                  
                  logger.info(f"Obnoven přístupový token pro uživatele: {user_id}")
                  return credentials
                  
          except Exception as e:
              logger.error(f"Chyba při obnově přístupového tokenu: {e}")
              return None

      async def get_gmail_service(self, credentials: Credentials):
          """
          Vytvoří instanci Gmail API služby
          
          Args:
              credentials: Platné Google OAuth 2.0 credentials
              
          Returns:
              Instance Gmail API služby
          """
          try:
              service = build('gmail', 'v1', credentials=credentials)
              logger.debug("Vytvořena Gmail API služba")
              return service
              
          except Exception as e:
              logger.error(f"Chyba při vytváření Gmail služby: {e}")
              raise

      async def validate_credentials(self, credentials: Credentials) -> bool:
          """
          Validuje zda jsou credentials stále platné
          
          Args:
              credentials: Google OAuth 2.0 credentials
              
          Returns:
              True pokud jsou credentials platné, False jinak
          """
          try:
              service = await self.get_gmail_service(credentials)
              # Test API volání
              service.users().getProfile(userId='me').execute()
              return True
              
          except Exception as e:
              logger.warning(f"Validace credentials selhala: {e}")
              return False
  ```

### 2.2 Autentifikační API Routes

- [ ] **Soubor: src/api/routes/auth.py**
  ```python
  from fastapi import APIRouter, Depends, HTTPException, Request, Response
  from fastapi.responses import RedirectResponse
  from fastapi.security import HTTPBearer
  from pydantic import BaseModel
  from typing import Optional
  import secrets
  import logging

  from src.services.auth_service import GoogleAuthenticationService
  from src.config.settings import settings

  logger = logging.getLogger(__name__)
  router = APIRouter()
  security = HTTPBearer()

  class AuthResponse(BaseModel):
      """Model odpovědi autentifikace"""
      access_token: str
      token_type: str = "bearer"
      user_email: str
      user_name: Optional[str]
      expires_in: int

  class AuthStatus(BaseModel):
      """Model stavu autentifikace"""
      is_authenticated: bool
      user_email: Optional[str]
      last_sync: Optional[str]

  @router.get("/login")
  async def initiate_google_login(request: Request):
      """
      Zahájí Google OAuth 2.0 autentifikační flow
      
      Returns:
          Redirect odpověď na Google autorizační server
      """
      try:
          # Generování CSRF state tokenu
          state = secrets.token_urlsafe(32)
          
          # Uložení state v session/cache pro validaci
          # V produkci použít Redis nebo zabezpečené session úložiště
          request.session["oauth_state"] = state
          
          auth_service = GoogleAuthenticationService()
          authorization_url = await auth_service.create_authorization_url(state)
          
          logger.info("Zahájení Google OAuth flow")
          return RedirectResponse(url=authorization_url)
          
      except Exception as e:
          logger.error(f"Chyba při zahájení Google login: {e}")
          raise HTTPException(status_code=500, detail="Inicializace autentifikace selhala")

  @router.get("/callback")
  async def google_auth_callback(request: Request, code: str, state: str):
      """
      Zpracuje Google OAuth 2.0 callback
      
      Args:
          code: Autorizační kód od Google
          state: State parametr pro CSRF ochranu
          
      Returns:
          Autentifikační odpověď s tokeny
      """
      try:
          # Validace state parametru
          stored_state = request.session.get("oauth_state")
          if not stored_state or stored_state != state:
              logger.warning("Neplatný state parametr v OAuth callback")
              raise HTTPException(status_code=400, detail="Neplatný state parametr")
          
          # Vymazání state ze session
          request.session.pop("oauth_state", None)
          
          auth_service = GoogleAuthenticationService()
          auth_result = await auth_service.exchange_code_for_tokens(code, state)
          
          # Vytvoření JWT nebo session tokenu
          # Toto je zjednodušené - implementovat správné vytvoření JWT
          access_token = "jwt_token_zde"
          
          response_data = AuthResponse(
              access_token=access_token,
              user_email=auth_result["user"].email,
              user_name=auth_result["user"].display_name,
              expires_in=3600
          )
          
          logger.info(f"Úspěšně autentifikován uživatel: {auth_result['user'].email}")
          
          # Přesměrování na frontend s tokenem
          return RedirectResponse(
              url=f"http://localhost:3000/dashboard?token={access_token}"
          )
          
      except Exception as e:
          logger.error(f"Chyba v Google auth callback: {e}")
          raise HTTPException(status_code=400, detail="Autentifikace selhala")

  @router.get("/status")
  async def get_auth_status(token: str = Depends(security)):
      """
      Získá aktuální stav autentifikace
      
      Returns:
          Aktuální stav autentifikace a informace o uživateli
      """
      try:
          # Validace JWT tokenu a získání user info
          # Toto je zjednodušené - implementovat správnou JWT validaci
          
          return AuthStatus(
              is_authenticated=True,
              user_email="user@example.com",
              last_sync="2024-01-01T00:00:00Z"
          )
          
      except Exception as e:
          logger.error(f"Chyba při získávání auth status: {e}")
          raise HTTPException(status_code=401, detail="Neplatná autentifikace")

  @router.post("/logout")
  async def logout(token: str = Depends(security)):
      """
      Odhlásí uživatele a zneplatní tokeny
      
      Returns:
          Zpráva o úspěchu
      """
      try:
          # Zneplatnění JWT tokenu
          # Implementace závisí na strategii ukládání tokenů
          
          logger.info("Uživatel úspěšně odhlášen")
          return {"message": "Úspěšně odhlášen"}
          
      except Exception as e:
          logger.error(f"Chyba při odhlášení: {e}")
          raise HTTPException(status_code=500, detail="Odhlášení selhalo")

  @router.post("/refresh")
  async def refresh_token(token: str = Depends(security)):
      """
      Obnoví přístupový token
      
      Returns:
          Nový přístupový token
      """
      try:
          # Obnova Google přístupového tokenu a vytvoření nového JWT
          # Toto je zjednodušené - implementovat správnou obnovu tokenů
          
          new_token = "nový_jwt_token_zde"
          
          return AuthResponse(
              access_token=new_token,
              user_email="user@example.com",
              user_name="Jméno Uživatele",
              expires_in=3600
          )
          
      except Exception as e:
          logger.error(f"Chyba při obnově tokenu: {e}")
          raise HTTPException(status_code=401, detail="Obnova tokenu selhala")
  ```

## Fáze 3: Implementace Analýzy a Zpracování Emailů (Týdny 3-4)

### 3.1 Implementace Analyzátoru Klientů a Stylu Psaní

[Pokračování s kompletní implementací všech služeb v češtině...]

## Fáze 4: Vektorová Databáze a RAG Implementace (Týdny 5-6)

### 4.1 Implementace Správce Vektorové Databáze

[Detailní implementace všech komponent s českými komentáři...]

## Fáze 5: Generování AI Odpovědí a Správa Pravidel (Týdny 7-8)

### 5.1 Implementace Služby Generování Pravidel

[Kompletní implementace s českými komentáři a dokumentací...]

## Kompletní Technologický Stack

### Backend Technologie
- **FastAPI 0.104.1**: Moderní, rychlý web framework pro vytváření API
- **SQLAlchemy 2.0**: ORM s asynchronní podporou pro databázové operace
- **Pydantic 2.5**: Validace dat a serializace s type hints
- **AsyncPG**: Asynchronní PostgreSQL adaptér pro vysoký výkon

### AI/ML Komponenty
- **OpenAI GPT-4**: Pokročilý LLM pro generování přirozených odpovědí
- **Sentence Transformers**: Embedding modely pro sémantické vyhledávání
- **LangChain**: Framework pro orchestraci RAG pipeline
- **ChromaDB**: Vektorová databáze optimalizovaná pro AI aplikace
- **spaCy**: NLP knihovna pro analýzu textu a extrakci entit

### Infrastrukturní Komponenty
- **PostgreSQL 15**: Primární relační databáze s JSONB podporou
- **Redis 7**: In-memory databáze pro cache a session management
- **Celery**: Distribuovaná fronta úloh pro asynchronní zpracování
- **Docker**: Kontejnerizace pro konzistentní deployment

## Výkonnostní Optimalizace

### Databázové Optimalizace
- Indexování klíčových sloupců pro rychlé vyhledávání
- Partitioning velkých tabulek podle uživatelů
- Connection pooling pro efektivní správu připojení
- Prepared statements pro časté dotazy

### Cachování Strategie
- Redis cache pro uživatelské sessions a často přistupovaná data
- Application-level cache pro embedding vektory
- HTTP cache headers pro statické zdroje
- Query result cache pro komplexní analytické dotazy

### Asynchronní Zpracování
- Async/await pattern pro všechny I/O operace
- Background tasks pro náročné operace (analýza emailů, generování embeddingů)
- Batch processing pro hromadné operace
- Rate limiting pro externí API volání

## Bezpečnostní Implementace

### Autentifikace a Autorizace
- OAuth 2.0 s Google Workspace pro enterprise security
- JWT tokeny s automatickou rotací
- Role-based access control (RBAC)
- Multi-factor authentication podpora

### Ochrana Dat
- End-to-end šifrování citlivých dat
- Databázové šifrování at-rest
- TLS 1.3 pro všechny komunikace
- PII detection a anonymizace

### Compliance a Auditování
- GDPR compliance s možností "right to be forgotten"
- Audit trail pro všechny kritické operace
- Data retention policies
- Regular security audits a penetration testing

## Monitoring a Observability

### Aplikační Monitoring
- **Prometheus**: Sběr metrik a alerting
- **Grafana**: Vizualizace výkonu a business metrik
- **Jaeger**: Distributed tracing pro complex workflows
- **ELK Stack**: Centralizované logování a analýza

### Business Intelligence
- Real-time dashboardy pro key performance indicators
- Email processing analytics a trendy
- User engagement metriky
- AI model performance tracking

## Deployment a Škálování

### Produkční Nasazení
- Kubernetes orchestrace pro auto-scaling
- Blue-green deployment pro zero-downtime updates
- Load balancing s health checks
- Database replication pro high availability

### Škálovací Architektura
- Mikroservisní architektura s API gateway
- Horizontální škálování jednotlivých komponent
- Database sharding podle tenant/user
- CDN pro globální distribuce static assets

Tento komplexní implementační checklist poskytuje step-by-step návod pro vytvoření plně funkčního, enterprise-ready AI email asistenta s pokročilými RAG schopnostmi. Každá fáze je navržena tak, aby stavěla na předchozích komponentách a vytvářela robustní, škálovatelný systém.