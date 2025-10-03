# Promo-Pack Submission Assistant

A SaaS tool that automates the creation of reference packs for promotional materials in the UK pharmaceutical industry.

## Guiding Principles

The "Promo-Pack" Submission Assistant
This is a new idea that is perfectly suited for a paid-only, niche model.

The High-Value Problem: In the UK, every piece of promotional material (sales aids, website copy, etc.) given to a doctor must be certified and can be requested by the regulatory body (PMCPA). If requested, the company must provide a "Reference Pack" – a perfectly collated PDF dossier containing the material itself, plus a copy of every single clinical paper and data source cited. Manually building this pack in Adobe Acrobat is an administrative nightmare that junior Brand Managers and Medical Affairs staff despise.

The SaaS Solution: A tool that automates the creation of these reference packs. The user uploads their final promotional piece and the folder of reference PDFs. The tool provides a simple interface to link each claim to the correct reference. It then automatically assembles, bookmarks, annotates, and outputs a single, compliant, submission-ready PDF dossier.

Why It Works as "Paid-Only": This is a true "painkiller" for a horrible, high-stakes task. The ROI is incredibly clear: it saves 10-15 hours of tedious administrative work and, more importantly, reduces the risk of an error-filled, rejected submission. It's a professional tool for a specific, painful job.

The 15-Minute Demo Pitch: "Hi [Brand Manager]. I know you probably spend days building reference packs for the PMCPA. I can show you how our tool can help you build a complete, perfectly formatted pack in under an hour. Can I show you how it works?"

That's an excellent and critical question. You've pinpointed the most common challenge in B2B SaaS: the person who feels the pain most acutely (the user) is often not the person with the budget (the buyer).

But this isn't a dealbreaker. In fact, it's a solvable problem that, when addressed correctly, defines a highly effective sales strategy.

Let's break down your two questions.

The "Junior User" Problem: Is It a Problem?
No, it's an opportunity. The strategy is not to sell to the junior person. The strategy is to empower the junior person to become your champion and sell the tool internally to their manager.

Your software needs to do more than just solve the user's problem; it needs to arm them with the business case to get it approved. The manager (the budget holder) doesn't care about saving the junior employee from a tedious task. They care about:

Time & Money: How much productive, expensive employee time is being wasted?

Risk: What is the compliance risk of an error-filled, manual submission?

Speed & Efficiency: How can their team get essential marketing materials to market faster?

So, the core of your product's sales pitch is arming that junior user with an undeniable ROI to present to their boss.

Pricing Strategy: How Much Could You Sell It For?
You need to anchor your price to the value delivered, not the cost of the software. Let's quantify it:

Manual Time: Building a reference pack for a moderately complex sales aid can take 10-15 hours of focused, administrative work.

Employee Cost: A junior Brand Manager or Medical Affairs associate in the UK has a fully-loaded cost to the business of roughly £30-£50 per hour.

Value per Use: A conservative estimate of 12 hours saved at £40/hour is £480 of value every single time they use the tool.

Your price needs to be a fraction of that, making it a "no-brainer" investment.

Here’s a potential pricing structure:

1. Professional Tier: £149 / month

Per User License: One person can use the software.

Features: Create up to 5 reference packs per month.

The Justification: "We are saving you over £400 in labour costs on your very first use each month. The tool pays for itself more than 3x over, every single time you use it."

2. Business Tier: £499 / month

Team License: Up to 5 users.

Features: Unlimited reference packs, team collaboration features, centralised dashboard for managers, audit trail.

The Justification: Aimed at the manager. "Equip your entire team, increase your department's throughput, and get a clear audit trail of all submissions for less than the cost of one wasted day of an employee's time."

This pricing is low enough for a department manager to approve without involving a lengthy, high-level procurement process, but high enough to build a very healthy, profitable subsidy business for you.

The Go-to-Market Strategy: Empowering Your Champion
Here’s how you solve the user vs. buyer problem in practice:

The "Wow" Demo: Your demo is for the junior user. It's fast, visual, and shows the "magic" of turning their most hated 12-hour task into a 1-hour job.

The Built-in ROI Report (Your Secret Weapon): This is the key. After a user builds a pack in your tool (either in the demo or a time-limited trial), the software should automatically generate a one-page summary PDF they can email to their boss. It would say:

Promo-Pack Assistant: Project Summary

Document Name: [User's Document Name]

Creation Time: 58 minutes

Estimated Manual Time: 12 hours

Time Saved on this Project: 11 hours

Equivalent Labour Cost Saved: ~£440

Compliance Benefit: 100% automated linking of claims to references reduces risk of manual error.

The Pitch: You literally give the junior user the business case. They don't have to awkwardly ask for money. They can go to their manager and say:
"I've found a tool that can save me over 10 hours on every single sales aid we produce. It costs £149 a month. Here's a report showing the savings from the one I just tested. Can we get it?"

That conversation is incredibly easy for a manager to say "yes" to. You've made their employee more efficient and reduced compliance risk for a trivial amount of money.

In summary: You're right to spot the user/buyer dynamic. But by pricing based on value and building the business case directly into the product, you turn that junior user from a penniless obstacle into your most powerful sales channel.

## Features

- Extracts key phrases (claims) from PDF documents
- RESTful API with authentication
- Docker containerized
- Asynchronous PDF download and processing

## API Specification

### Endpoint: `POST /extract-claims`

**Authentication:** Include `X-API-Key` header with your secret key.

**Request Body:**
```json
{
  "document_url": "https://example.com/path/to/document.pdf"
}
```

**Response:**
```json
{
  "claims": [
    {
      "text": "Drug X was shown to reduce Y by Z%",
      "page": 1,
      "confidence_score": 0.92
    }
  ]
}
```

### Health Check Endpoints

#### `GET /health`
Basic health check for load balancers and monitoring systems.

**Response:**
```json
{
  "status": "healthy",
  "service": "promopack-extractor",
  "version": "1.0"
}
```

#### `GET /ready`
Readiness probe for container orchestration systems. Checks if the service is ready to handle requests.

**Response:**
```json
{
  "status": "ready",
  "service": "promopack-extractor",
  "version": "1.0"
}
```
Or if not ready:
```json
{
  "status": "not ready",
  "reason": "LANGEXTRACT_API_KEY not configured"
}
```

## Developer Documentation

For comprehensive API documentation including detailed setup instructions, authentication, error handling, code examples, and troubleshooting, see [DEVELOPER_API.md](DEVELOPER_API.md).

## Quick Start

### The Fastest Way (Recommended)

1. **Configure your API keys:**
   ```bash
   cp .env.example .env
   # Edit .env with your actual API keys
   ```

2. **Run the quick start script:**
   ```bash
   # Linux/macOS
   ./run.sh
   
   # Windows
   run.bat
   
   # Or use Make (Podman)
   make setup-dev  # Configure environment
   make podman-run # Build and run with Podman
   
   # Or use Make (Docker)
   make setup-dev  # Configure environment
   make docker-build && make docker-run # Build and run with Docker
   ```

3. **Access the API:**
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

### Manual Setup

If you prefer to run commands manually, see the detailed instructions below.

1. **Set up environment variables:**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env with your actual API keys
   # Required: API_KEY_SECRET and LANGEXTRACT_API_KEY
   ```

2. **Build the container image:**
   ```bash
   podman build -t promopack-extractor:latest .
   ```

3. **Run the container:**
   ```bash
   # For development with SQLite database
   podman run -d --name promopack-extractor \
     -p 8000:8000 \
     -e API_KEY_SECRET=your-api-key-here \
     -e LANGEXTRACT_API_KEY=your-langextract-key-here \
     -e DATABASE_URL=sqlite:///./dev.db \
     -e ENV=dev \
     promopack-extractor:latest
   
   # For production with persistent database
   podman run -d --name promopack-extractor \
     -p 8000:8000 \
     -v /path/to/data:/app/data \
     -e API_KEY_SECRET=your-production-api-key \
     -e LANGEXTRACT_API_KEY=your-production-langextract-key \
     -e DATABASE_URL=sqlite:///./prod.db \
     -e ENV=prod \
     promopack-extractor:latest
   ```

4. **Verify the deployment:**
   ```bash
   # Check container status
   podman ps
   
   # View logs
   podman logs promopack-extractor
   
   # Test health endpoint
   curl http://localhost:8000/health
   
   # Access API documentation
   open http://localhost:8000/docs
   ```

5. **Stop the container:**
   ```bash
   podman stop promopack-extractor
   podman rm promopack-extractor
   ```

### Using Docker

If you prefer to use Docker instead of Podman, follow these instructions:

1. **Set up environment variables:** (same as above)
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env with your actual API keys
   # Required: API_KEY_SECRET and LANGEXTRACT_API_KEY
   ```

2. **Build the container image:**
   ```bash
   docker build -t promopack-extractor:latest .
   ```

3. **Run the container:**
   ```bash
   # For development with SQLite database
   docker run -d --name promopack-extractor \
     -p 8000:8000 \
     -e API_KEY_SECRET=your-api-key-here \
     -e LANGEXTRACT_API_KEY=your-langextract-key-here \
     -e DATABASE_URL=sqlite:///./dev.db \
     -e ENV=dev \
     promopack-extractor:latest
   
   # For production with persistent database
   docker run -d --name promopack-extractor \
     -p 8000:8000 \
     -v /path/to/data:/app/data \
     -e API_KEY_SECRET=your-production-api-key \
     -e LANGEXTRACT_API_KEY=your-production-langextract-key \
     -e DATABASE_URL=sqlite:///./prod.db \
     -e ENV=prod \
     promopack-extractor:latest
   ```

4. **Verify the deployment:**
   ```bash
   # Check container status
   docker ps
   
   # View logs
   docker logs promopack-extractor
   
   # Test health endpoint
   curl http://localhost:8000/health
   
   # Access API documentation
   open http://localhost:8000/docs
   ```

5. **Stop the container:**
   ```bash
   docker stop promopack-extractor
   docker rm promopack-extractor
   ```

### Environment Variables

**Required:**
- `API_KEY_SECRET`: Secret key for API authentication
- `LANGEXTRACT_API_KEY`: API key for Google Gemini LLM service

**Optional:**
- `ENV`: Environment mode (`dev` or `prod`, defaults to `dev`)
- `DATABASE_URL`: Database connection string (defaults to `sqlite:///./dev.db` for dev, `sqlite:///./prod.db` for prod)
- `LOG_TO_FILE`: Whether to log to file (`true`/`false`, defaults to `false`)
- `LOG_LEVEL`: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, defaults to `INFO` for prod, `DEBUG` for dev)
- `RATE_LIMIT_REQUESTS`: Number of requests allowed per window (default: 100 for dev, 10 for prod)
- `RATE_LIMIT_WINDOW`: Rate limit time window in seconds (default: 60)
- `MAX_FILE_SIZE`: Maximum PDF file size in bytes (default: 20MB for prod, 10MB for dev)
- `MAX_PAGES`: Maximum pages to process (default: 1000 for prod, 500 for dev)
- `REQUEST_TIMEOUT`: HTTP request timeout in seconds (default: 30.0)

## Development

### Local Development Setup

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

2. **Set up environment variables:**
   ```bash
   # For Windows PowerShell
   $env:API_KEY_SECRET="your-dev-api-key"
   $env:LANGEXTRACT_API_KEY="your-dev-langextract-key"
   
   # For Linux/macOS
   export API_KEY_SECRET="your-dev-api-key"
   export LANGEXTRACT_API_KEY="your-dev-langextract-key"
   ```

3. **Run the application:**
   ```bash
   # Development mode with auto-reload
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   
   # Production mode
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

4. **Run tests:**
   ```bash
   # Run all tests
   pytest
   
   # Run with coverage
   pytest --cov=. --cov-report=html
   
   # Run specific test file
   pytest tests/test_api.py
   ```

### Database Management

The application uses SQLAlchemy with async support. Database tables are automatically created on startup.

**For development (SQLite):**
- Database file: `dev.db` (created automatically)
- No additional setup required

**For production (PostgreSQL recommended):**
```bash
# Set DATABASE_URL to your PostgreSQL connection string
export DATABASE_URL="postgresql+asyncpg://user:password@host:port/database"
```

### API Testing

```bash
# Test the health endpoint
curl http://localhost:8000/health

# Test claim extraction (replace with real PDF URL)
curl -X POST "http://localhost:8000/extract-claims" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"document_url": "https://example.com/sample.pdf"}'

# View API documentation
open http://localhost:8000/docs
```