# Deploy Guide

## Requirements
- Docker + Docker Compose
- API keys: OpenRouter, Firecrawl, Telegram (one bot per state channel)

---

## First deploy

```bash
# 1. Clone the repo
git clone <repo> && cd Realtor_AI

# 2. Create real env files from the examples (one per state)
cp envs/florida.env.example     envs/florida.env
cp envs/texas.env.example       envs/texas.env
cp envs/california.env.example  envs/california.env
# → Edit each .env with real API keys and Telegram credentials

# 3. Build image and start all state containers
docker compose up -d --build
```

---

## Add a new state

```bash
cp envs/florida.env.example envs/newstate.env
# Edit envs/newstate.env with the new state's values

# Add a service block to docker-compose.yml following the existing pattern
docker compose up -d --build newstate
```

---

## Useful commands

```bash
# Live logs for a container
docker compose logs -f florida

# Pipeline log inside the container
docker exec realtor_florida tail -f /app/logs/cron.log

# Restart one container (e.g. after editing its .env)
docker compose restart texas

# Stop everything
docker compose down
```

---

## Cron schedule (UTC)

| State      | Time (EST) | UTC cron       |
|------------|------------|----------------|
| Florida    | 9:00 AM    | `0 14 * * 1-5` |
| Texas      | 10:00 AM   | `0 15 * * 1-5` |
| California | 11:00 AM   | `0 16 * * 1-5` |

Change the schedule by editing `CRON_SCHEDULE` in the state's `.env` file and running `docker compose restart <state>`.
