# 🧩 PM Hub — Backend (FastAPI)

Backend servis za Trello-like aplikaciju **PM Hub**. Pruža REST API za timove, board-ove, liste i kartice (Epic → Story → Task), kao i labele, članove, komentare, priloge, sprintove i notifikacije.

---

## ✨ Stack

| Tehnologija | Uloga |
|---|---|
| 🐍 **Python** | Jezik |
| ⚡ **FastAPI** | Web framework (auto Swagger `/docs`) |
| 🐘 **PostgreSQL** | Baza podataka |
| 📦 **SQLAlchemy** | ORM sloj |
| 🧬 **Pydantic** | Validacija/šeme |
| 🐳 **Docker Compose** | Lokalni razvoj |
| 🧭 **Alembic** | (opciono) migracije šeme |

> Front je rađen u React + Vite + Tailwind (dev server tipično na `http://localhost:5173`), pa su CORS origin-i već podešeni u primeru ispod.  

---

## 🚀 Quick start

### Varijanta A — Docker (preporučeno)
1. Napravi `.env` na osnovu `.env.example` (primer ispod).
2. Pokreni:
   ```bash
   docker compose up --build