# Reliable-Event-Processing-Service
Systems that process background jobs often fail silently, retry incorrectly, or duplicate work. This project builds a reliable event-processing backend that guarantees delivery, handles retries safely, and scales.

## Core Features:
1) Allows a user to access a number of endpoints, submitting jobs/events
2) The system processes jobs and/or events in an asynchronous manner
3) Upon process failures, jobs are re-tried accordingly
4) The system gaurantees that no process or event is duplicated
5) State persistance is ensured via Postgres database

## Tech Stack
- **Language**: Python
- **Framework**: FastAPI
- **Database**: Postgres
- **Async Tasks**: Background worker/Chron Job *(To be decided)*

## Prerequisites

- Python 3.8 or higher
- Git (optional, if cloning from repo)
- PostgreSQL (for later DB integration, optional for Week 1 stub)

---

### 1. Clone the repository (optional)

```bash
git clone <repo-url>
cd Reliable-Event-Processing-Service
```

### 2. Create a virtual environment

It's recommended to use a virtual environment to isolate dependencies.

##### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

##### macOS/Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the server
Run the FastAPI app using Uvicorn:

```bash
uvicorn app.main:app
```
