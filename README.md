# Reliable-Event-Processing-Service
Systems that process background jobs often fail silently, retry incorrectly, or duplicate work. This project builds a reliable event-processing backend that guarantees delivery, handles retries safely, and scales.

## Core Features:
1) Allows a user to access a number of endpoints, submitting jobs/events
2) The system processes jobs and/or events in an asynchronous manner
3) Upon process failures, jobs are re-tried accordingly
4) The system gaurantees that no process or event is duplicated
5) State persistance is ensured via Postgres database

## Technial Stack
- **Language**: Python
- **Framework**: FastAPI
- **Database**: Postgres
- **Async Tasks**: Background worker/Chron Job *(To be decided)*