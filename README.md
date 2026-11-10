# SecFlow Demo — E-Commerce Customer Web Application

This repository contains the official adapted demo customer web application used for **SecFlow** security scanning, architecture synthesis, and AWS ECS on EC2 deployment testing.

> **Attribution & Licensing:**  
> Adapted from the open-source project by Victor Delis under the **MIT License**.  
> The original license and copyright notices are preserved in full in the [`LICENSE`](./LICENSE) file.

---

## 1. Application Architecture

The application is a modern, multi-tier full-stack e-commerce solution:

| Component | Technology | Default Port | Description |
| :--- | :--- | :---: | :--- |
| **Customer Storefront** | React 18, React Router v6, Tailwind CSS | `3000` | Public storefront with product catalog, cart, and simulated checkout |
| **Admin Portal** | React 18, Tailwind CSS | `5030` | Administrative dashboard for inventory, orders, and store statistics |
| **Core API Backend** | FastAPI (Python 3.11), SQLAlchemy 2, Uvicorn | `8000` | REST API with JWT authentication, cart calculations, and order creation |
| **Relational Database** | PostgreSQL 16 (Alpine) | `5432` | Relational store for users, products, orders, and order items |
| **Cache Tier** | Redis 7 (Alpine) | `6379` | Optional caching tier for sessions and fast retrieval |

---

## 2. Security Hardening & Adaptations for SecFlow

This adapted version includes several critical operational and security enhancements:
1. **Supply Chain Hardening:** Excised third-party obfuscated scripts from build configurations.
2. **Container Least Privilege:** Configured non-root execution (`USER 10001` / `USER appuser` in backend and `USER nginx` in frontends).
3. **Database Version Compatibility:** Aligned with PostgreSQL 16 to match production cloud database engines (AWS RDS PostgreSQL 16.x).
4. **Standard Orchestration Probes:** Added `/health/live` (liveness) and `/health/ready` (readiness) probes in addition to base `/health`.
5. **Decoupled Cloud Storage:** Supports local persistent volume storage (`/app/uploads`) when cloud storage (GCS/S3) is not configured.
6. **Network Isolation:** Database port 5432 is kept internal to the container network and not bound to public host interfaces.

---

## 3. Getting Started (Local Development)

### 3.1 Prerequisites
- Docker Engine 24+ and Docker Compose v2+
- Git

### 3.2 Environment Configuration
Copy the provided `.env.example` to `.env`:
```bash
cp .env.example .env
```
Customize environment variables as needed. All variables provide safe local defaults out of the box.

### 3.3 Starting the Services
Build and start all 5 services in detached mode:
```bash
docker compose up -d --build
```

### 3.4 Checking Health & Logs
Check container status:
```bash
docker compose ps
```
Verify the backend health probe:
```bash
curl http://localhost:8000/health/ready
# Expected: {"status":"ready"}
```

---

## 4. Endpoints & Access URLs

Once launched, the following interfaces are available:

- **Customer Storefront:** [http://localhost:3000](http://localhost:3000)
- **Admin Portal:** [http://localhost:5030](http://localhost:5030)
- **FastAPI Documentation (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

---

## 5. Seed Data & Demo Accounts

On startup, the database automatically initializes tables and populates sample catalog products and demo credentials:

* **Customer Test Account:**
  * **Email:** `test@example.com`
  * **Password:** `password`
  * **Role:** Customer (can browse catalog, add items to cart, and place simulated orders)

* **Administrator Account:**
  * **Email:** `admin@ecommerce.com`
  * **Password:** `admin123`
  * **Role:** Administrator (can access the admin portal at port 5030 to review orders and catalog items)

---

## 6. Stopping the Services

To shut down the local environment:
```bash
docker compose down
```
To also remove persistent database volumes:
```bash
docker compose down -v
```

---

## 7. License

Distributed under the **MIT License**. See [`LICENSE`](./LICENSE) for more information.
