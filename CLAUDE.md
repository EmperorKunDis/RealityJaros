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
- **setup_wizard.py**: 8krokový průvodce nastavením pro nové uživatele
- **monitoring.py**: Monitorování e-mailů každou minutu
- **ultimate_prompts.py**: Generování ultimátních promptů na základě uživatelského profilu
- **auto_send.py**: Automatické odesílání e-mailů s konfiguratelnými pravidly
- **gdpr_compliance.py**: Compliance s EU GDPR včetně správy souhlasů a práv subjektů údajů

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

## Příklady API volání

### Základní operace
```bash
# Kontrola stavu aplikace
curl -X GET "http://localhost:8000/health"

# Synchronizace e-mailů
curl -X POST "http://localhost:8000/api/v1/emails/sync"

# Analýza klientů
curl -X POST "http://localhost:8000/api/v1/clients/analyze"

# Analýza stylu psaní
curl -X POST "http://localhost:8000/api/v1/analysis/style"

# Analýza témat
curl -X POST "http://localhost:8000/api/v1/analysis/topics"
```

### Vektorové databázové operace
```bash
# Inicializace vektorových kolekcí
curl -X POST "http://localhost:8000/api/v1/vectors/initialize"

# Kontrola stavu vektorové databáze
curl -X GET "http://localhost:8000/api/v1/vectors/health"

# Statistiky kolekcí
curl -X GET "http://localhost:8000/api/v1/vectors/collections/stats"

# Vektorizace e-mailů
curl -X POST "http://localhost:8000/api/v1/vectors/vectorize" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "force_reindex": false}'

# Sémantické vyhledávání
curl -X POST "http://localhost:8000/api/v1/vectors/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "deadline projektu", "max_results": 5}'
```

### RAG-powered generování odpovědí
```bash
# Generování odpovědi pomocí RAG
curl -X POST "http://localhost:8000/api/v1/responses/generate-rag/email123" \
  -H "Content-Type: application/json"

# Generování odpovědi s možnostmi
curl -X POST "http://localhost:8000/api/v1/responses/generate" \
  -H "Content-Type: application/json" \
  -d '{"email_id": "email123", "strategy": "hybrid", "formality": "formal"}'
```

### Průvodce nastavením (8 kroků)
```bash
# Zahájení průvodce nastavením
curl -X POST "http://localhost:8000/api/v1/setup-wizard/start"

# Dokončení kroku 1 (Google Auth)
curl -X POST "http://localhost:8000/api/v1/setup-wizard/step-1" \
  -H "Content-Type: application/json" \
  -d '{"google_authenticated": true, "gmail_access": true}'

# Dokončení kroku 2 (Preference e-mailů)
curl -X POST "http://localhost:8000/api/v1/setup-wizard/step-2" \
  -H "Content-Type: application/json" \
  -d '{"sync_frequency": "realtime", "working_hours_start": "09:00", "working_hours_end": "17:00"}'

# Kontrola postupu průvodce
curl -X GET "http://localhost:8000/api/v1/setup-wizard/progress"
```

### Monitorování e-mailů a automatizace
```bash
# Kontrola stavu monitorování
curl -X GET "http://localhost:8000/api/v1/monitoring/status"

# Spuštění manuálního monitorování
curl -X POST "http://localhost:8000/api/v1/monitoring/trigger"

# Konfigurace automatického odesílání
curl -X POST "http://localhost:8000/api/v1/auto-send/configure" \
  -H "Content-Type: application/json" \
  -d '{"auto_respond_enabled": true, "confidence_threshold": 0.8, "delay_minutes": 5}'

# Zpracování fronty automatického odesílání
curl -X POST "http://localhost:8000/api/v1/auto-send/process-queue"
```

### Generování ultimátních promptů
```bash
# Generování prompta na základě uživatelského profilu
curl -X POST "http://localhost:8000/api/v1/prompts/generate-ultimate" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "context_type": "email_response"}'

# Získání profilové analýzy uživatele
curl -X GET "http://localhost:8000/api/v1/prompts/user-profile/user123"

# Aktualizace profilových pravidel
curl -X POST "http://localhost:8000/api/v1/prompts/profile-rules" \
  -H "Content-Type: application/json" \
  -d '{"formality_preference": "semi-formal", "response_length": "medium"}'
```

### Google Services integrace
```bash
# Nastavení Google Services pověření
curl -X POST "http://localhost:8000/api/v1/google/credentials/setup" \
  -H "Content-Type: application/json" \
  -d '{"service_type": "sheets", "access_token": "token", "refresh_token": "refresh", "scopes": ["https://www.googleapis.com/auth/spreadsheets"]}'

# Kontrola stavu Google služeb
curl -X GET "http://localhost:8000/api/v1/google/credentials/status"

# Vytvoření Google Sheets integrace
curl -X POST "http://localhost:8000/api/v1/google/sheets/integrations" \
  -H "Content-Type: application/json" \
  -d '{"spreadsheet_id": "1234", "spreadsheet_name": "Email Log", "sheet_name": "Emails", "integration_type": "email_log", "column_mapping": {"A": "timestamp", "B": "sender", "C": "subject"}}'

# Synchronizace dat do Google Sheets
curl -X POST "http://localhost:8000/api/v1/google/sheets/integration123/sync"

# Vytvoření Google Docs šablony
curl -X POST "http://localhost:8000/api/v1/google/docs/templates" \
  -H "Content-Type: application/json" \
  -d '{"template_name": "Email Summary", "template_type": "email_summary", "template_content": "Shrnutí e-mailů za {date}", "placeholder_mapping": {"date": "summary.date"}}'

# Generování dokumentu ze šablony
curl -X POST "http://localhost:8000/api/v1/google/docs/generate" \
  -H "Content-Type: application/json" \
  -d '{"template_id": "template123", "document_title": "Týdenní přehled", "generation_data": {"summary": {"date": "2024-01-15"}}}'

# Vytvoření automatizovaného workflow
curl -X POST "http://localhost:8000/api/v1/google/workflows" \
  -H "Content-Type: application/json" \
  -d '{"workflow_name": "Auto Email Sync", "trigger_type": "new_email", "workflow_steps": [{"type": "sheets_update", "integration_id": "integration123"}]}'

# Spuštění workflow
curl -X POST "http://localhost:8000/api/v1/google/workflows/workflow123/execute" \
  -H "Content-Type: application/json" \
  -d '{"trigger_data": {"email_id": "email123"}}'

# Získání předpřipravených workflow šablon
curl -X GET "http://localhost:8000/api/v1/google/workflows/templates"

# Kontrola zdraví Google integrace
curl -X GET "http://localhost:8000/api/v1/google/health"
```

### GDPR Compliance a ochrana dat
```bash
# Záznam souhlasu uživatele
curl -X POST "http://localhost:8000/api/v1/gdpr/consent" \
  -H "Content-Type: application/json" \
  -d '{"consent_type": "email_processing", "consent_text": "Souhlasím se zpracováním e-mailů", "legal_basis": "consent", "data_categories": ["contact_data"], "consent_method": "api"}'

# Odvolání souhlasu
curl -X POST "http://localhost:8000/api/v1/gdpr/consent/withdraw" \
  -H "Content-Type: application/json" \
  -d '{"consent_type": "email_processing"}'

# Kontrola stavu souhlasu
curl -X GET "http://localhost:8000/api/v1/gdpr/consent/email_processing/status"

# Žádost o přístup k datům (GDPR čl. 15)
curl -X POST "http://localhost:8000/api/v1/gdpr/data-subject-request" \
  -H "Content-Type: application/json" \
  -d '{"request_type": "access", "request_description": "Požadavek na všechna moje data"}'

# Export uživatelských dat (GDPR čl. 20)
curl -X GET "http://localhost:8000/api/v1/gdpr/export-data"

# Nastavení soukromí
curl -X GET "http://localhost:8000/api/v1/gdpr/privacy-settings"
curl -X PUT "http://localhost:8000/api/v1/gdpr/privacy-settings" \
  -H "Content-Type: application/json" \
  -d '{"allow_email_analysis": true, "marketing_emails": false, "auto_delete_emails_after_days": 365}'

# Kategorie zpracovávaných dat
curl -X GET "http://localhost:8000/api/v1/gdpr/data-categories"

# Právní základy zpracování
curl -X GET "http://localhost:8000/api/v1/gdpr/legal-bases"
```

### Správa úloh na pozadí
```bash
# Zobrazení stavu úloh
curl -X GET "http://localhost:8000/api/v1/tasks/status"

# Spuštění analýzy e-mailu
curl -X POST "http://localhost:8000/api/v1/tasks/analyze-email" \
  -H "Content-Type: application/json" \
  -d '{"email_id": "email123", "user_id": "user123"}'

# Získání výsledku úlohy
curl -X GET "http://localhost:8000/api/v1/tasks/result/task123"
```

## Ultimate AI Email Agent funkce

Tento systém nyní implementuje všechny funkce specifikované v designovém dokumentu "Ultimativní AI E-mailový Agent":

### Implementované vysokohodnotné funkce
1. **8krokový průvodce nastavením** - Kompletní onboarding proces s integrací Google Services
2. **Minutové monitorování e-mailů** - Automatické sledování nových e-mailů každou minutu
3. **Systém generování ultimátních promptů** - Dynamické vytváření promptů na základě uživatelského profilu
4. **Automatické odesílání e-mailů** - Konfigurovatelná pravidla a denní přehledy
5. **Compliance s EU GDPR** - Komplexní ochrana dat, správa souhlasů a práva subjektů údajů
6. **Google Services integrace** - Automatizace s Google Sheets, Docs, Drive a workflow systém

### Google Workspace integrace funkce
- **Google Sheets automatizace** - Automatická synchronizace e-mailových dat, klientských statistik a metrik odpovědí
- **Google Docs generování** - Šablony pro automatické vytváření týdenních přehledů, klientských reportů a shrnutí
- **Google Drive správa** - Organizace souborů podle klientů a projektů s automatickým mapováním
- **Workflow automatizace** - Spouštěče založené na událostech (nový e-mail, odpověď AI, denní přehled)
- **Předpřipravené šablony** - Email-to-Sheets sync, týdenní reporty, sledování odpovědí klientům

### Architektonické vylepšení
- **Middleware pro GDPR audit** - Automatické logování přístupu k datům
- **Celery úlohy pro compliance** - Automatické čištění dat a kontrola souhlasů
- **Vícevrstvá ochrana dat** - Šifrování, anonymizace a pseudonymizace
- **Auditní protokoly** - Kompletní sledovatelnost všech operací s daty
- **Google API integrace** - OAuth 2.0 flow s automatickou aktualizací tokenů
- **Workflow orchestrace** - Komplexní systém automatizace s retry logikou a monitoringem

Toto je systém připravený k produkčnímu prostředí s komplexním testováním (8 testovacích modulů), ověřováním nasazení a architekturou podnikové úrovně podporující horizontální škálování a nasazení mikroslužeb.