# CLAUDE.md

Tento soubor poskytuje Claude Codeovi (claude.ai/code) návod pro práci s kódem v tomto repozitáři.

## Přehled projektu

Jedná se o plně implementovaný systém e-mailového asistenta s umělou inteligencí, který je navržen pro analýzu e-mailových vzorců, pochopení stylů psaní a generování kontextových e-mailových odpovědí pomocí technologie RAG (Retrieval-Augmented Generation). Projekt se řídí komplexní podnikovou architekturou s backendem FastAPI, frontendem React a úložištěm pro více databází.

## Architektura

### Backend (Python FastAPI)
- **Vrstva API**: FastAPI se 7 moduly tras (`src/api/routes/`)
- **Vrstva služeb**: 10+ služeb obchodní logiky (`src/services/`)
- **Datová vrstva**: Asynchronní modely SQLAlchemy + vektorové úložiště ChromaDB
- **Zpracování na pozadí**: Celery s Redis brokerem
- **Autentizace**: Integrace Google OAuth 2.0

### Frontend (React TypeScript)
- **Framework**: Vite + React 18 + TypeScript
- **Knihovna uživatelského rozhraní**: Komponenty uživatelského rozhraní Radix se styly shadcn/ui
- **Správa stavu**: React Query pro stav API, kontext pro autorizaci
- **Styling**: Tailwind CSS s vlastním designovým systémem

### Infrastruktura
- **PostgreSQL**: Primární relační databáze
- **ChromaDB**: Vektorová databáze pro sémantické vyhledávání (8 specializovaných kolekcí)
- **Redis**: Ukládání do mezipaměti a Celery message broker
- **Docker**: Multi-service contejnerizace

## Běžné vývojové příkazy

### Nastavení prostředí
```bash
# Nastavení backendu
python -m venv venv
source venv/bin/activate # Mac/Linux
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Nastavení frontendu
cd frontend
npm install
```

### Spuštění aplikace
```bash
# Úplné nasazení Dockeru (doporučeno)
docker-compose -f docker/docker-compose.yml up -d

# Pouze backend (s externími službami)
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Vývojový server frontendu
cd frontend && npm run dev
```

### Zpracování na pozadí
```bash
# Spuštění Celery worker a plánovač
python scripts/start_celery_worker.py --concurrency 4
python scripts/start_celery_beat.py
```

### Testování
```bash
# Backendové testy
pytest src/tests/ # Všechny testy
pytest src/tests/test_main.py # Specifický testovací soubor
pytest src/tests/ -v --cov=src/ # S pokrytím

# Ověření nasazení
python scripts/deployment_verification.py
```

### Přístup k API
- **Dokumentace**: http://localhost:8000/docs (Swagger UI)
- **Alternativní dokumentace**: http://localhost:8000/redoc
- **Kontrola stavu**: http://localhost:8000/health
- **Frontend**: http://localhost:3000

## Klíčové systémové komponenty

### Základní služby (`src/services/`)
- **ResponseGeneratorService**: Generování odpovědí s více strategiemi (RAG/Rule/Hybrid/Template)
- **RAGEngine**: Generování s rozšířeným vyhledáváním a načítáním pomocí LangChainu
- **VectorDatabaseManager**: ChromaDB s 8 specializovanými kolekcemi
- **EmailAnalyzer**: Analýza e-mailů, analýza klientů a rozpoznávání vzorů
- **StyleAnalyzer**: Profilování stylu psaní založené na NLP
- **AuthService**: Google OAuth 2.0 se správou tokenů JWT

### Koncové body API (`src/api/routes/`)
- **auth.py**: Ověřování a správa uživatelů
- **emails.py**: Načítání, analýza a analýza e-mailů
- **clients.py**: Správa vztahů s klienty
- **responses.py**: Koncové body generování odpovědí pomocí umělé inteligence
- **analysis.py**: Analýza stylu psaní a tématu
- **vectors.py**: Operace s vektorovou databází a sémantické vyhledávání
- **tasks.py**: Správa úloh na pozadí

### Databázové modely (`src/models/`)
- **Uživatel**: Profily a preference ověřování
- **EmailMessage**: Obsah e-mailu s metadaty a výsledky analýzy
- **Klient**: Sledování vztahů a komunikační vzorce
- **Response**: Generované odpovědi s metrikami kvality

## Vývojový postup

### Při přidávání nových funkcí
1. **Vrstva služeb**: Implementace obchodní logiky v `src/services/`
2. **Vrstva API**: Přidání koncových bodů do příslušného modulu `src/api/routes/`
3. **Modely**: V případě potřeby rozšíření databázových modelů v `src/models/`
4. **Testy**: Přidání komplexních testů v `src/tests/`
5. **Frontend**: Aktualizace komponent React v `frontend/src/`

### Při práci s komponentami AI
- **Vektorové operace**: Používejte `VectorDatabaseManager` pro ChromaDB operace
- **Implementace RAG**: Rozšíření `RAGEngine` pro nové strategie vyhledávání
- **Generování odpovědí**: Úprava `ResponseGeneratorService` pro nové metody generování
- **Analýza stylů**: Aktualizace `StyleAnalyzer` pro nové lingvistické funkce

### Při ladění
- **Backendové protokoly**: Kontrola `logs/app.log` nebo protokolů Dockeru
- **Databáze**: Použít asynchronní relaci SQLAlchemy z `src/config/database.py`
- **Vektorová databáze**: Přístup ke kolekcím ChromaDB prostřednictvím správce vektorů
- **Testování API**: Použít automatické uživatelské rozhraní Swagger od FastAPI na `/docs`
## Důležité poznámky

- **Async v celém rozsahu**: Všechny databázové operace a externí volání API používají async/await
- **Multi-Database**: PostgreSQL pro relační data, ChromaDB pro vektory, Redis pro ukládání do mezipaměti
- **Zpracování na pozadí**: Dlouhodobě běžící úlohy (analýza e-mailů, vektorizace) používají Celery
- **Vyžadováno ověřování**: Většina koncových bodů vyžaduje ověřování Google OAuth 2.0
- **Vector Search**: Sémantické vyhledávání v 8 specializovaných kolekcích s prahovými hodnotami podobnosti
- **Strategie odezvy**: Systém podporuje generování záložních kolekcí RAG, založených na pravidlech, hybridních a šablonových řešení

## Bezpečnostní aspekty

- Tok OAuth 2.0 s integrací Google Workspace
- Tokeny JWT se správným ověřováním a rotací obnovování
- Middleware pro CORS, důvěryhodné hostitele a ověřování požadavků
- Mechanismy detekce PII a ochrany dat
- Komplexní zpracování chyb bez úniku informací

## Struktura frontendu

### Klíčové komponenty (`frontend/src/components/`)
- **Dashboard**: Hlavní rozhraní aplikace
- **EmailPreview**: Zobrazení e-mailů s výsledky analýzy
- **ClientAnalytics**: Vizualizace vztahů s klienty
- **AIInsights**: Rozhraní pro generování odpovědí
- **ui/**: Opakovaně použitelné komponenty shadcn/ui

### Správa stavu
- **AuthContext**: Stav ověření uživatele
- **AppContext**: Globální stav aplikace
- **React Query**: Ukládání a synchronizace stavu serveru do mezipaměti
- **Vlastní hooky**: `useEmails`, `useClients`, `useResponses`

Toto je systém připravený k produkčnímu prostředí s komplexním testováním (8 testovacích modulů), ověřováním nasazení a architekturou podnikové úrovně podporující horizontální škálování a nasazení mikroslužeb.