from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import uvicorn
import os

# CRITICAL: Import settings with error handling - don't block if it fails
try:
    from app.config import settings
except Exception as e:
    print(f"⚠️ Warning: Could not import settings: {e}", flush=True)
    # Create minimal settings
    class MinimalSettings:
        allowed_origins = ["*"]
        host = "0.0.0.0"
        port = int(os.getenv("PORT", "8080"))
        debug = False
    settings = MinimalSettings()

# CRITICAL: Import database with error handling - don't block if it fails
try:
    from app.database import init_db
except Exception as e:
    print(f"⚠️ Warning: Could not import database: {e}", flush=True)
    init_db = None

# Import routers individually with error handling - so one failure doesn't break all
# CRITICAL: Ensure dependencies are available first
routers = {}
router_names = ['auth', 'products', 'cart', 'orders', 'admin', 'upload', 'favorites']

# Ensure critical dependencies exist before importing routers
try:
    from app.database import get_db
    print("✅ Database dependency available", flush=True)
except Exception as e:
    print(f"⚠️ Warning: Database dependency not available: {e}", flush=True)

try:
    from app.config import JWT_CONFIG
    print("✅ JWT config available", flush=True)
except Exception as e:
    print(f"⚠️ Warning: JWT config not available: {e}", flush=True)

try:
    from app.models import User, Product, Order
    print("✅ Models available", flush=True)
except Exception as e:
    print(f"⚠️ Warning: Models not available: {e}", flush=True)

# Now import routers
for router_name in router_names:
    try:
        print(f"🔍 Attempting to import router '{router_name}'...", flush=True)
        router_module = __import__(f'app.routers.{router_name}', fromlist=[router_name])
        router_obj = getattr(router_module, 'router', None)
        if router_obj:
            routers[router_name] = router_obj
            print(f"✅ Router '{router_name}' imported and registered successfully", flush=True)
        else:
            print(f"⚠️ Warning: Router '{router_name}' module found but no 'router' attribute", flush=True)
            routers[router_name] = None
    except Exception as e:
        print(f"❌ ERROR: Router '{router_name}' failed to import: {e}", flush=True)
        import traceback
        traceback.print_exc()
        routers[router_name] = None

# Application lifespan - CRITICAL: Must be fast and never block
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - mark ready IMMEDIATELY
    import sys
    print("🚀 Starting E-commerce Store Backend...", flush=True)
    print(f"📦 Python version: {sys.version}", flush=True)
    print(f"🌐 PORT environment variable: {os.getenv('PORT', 'not set')}", flush=True)
    
    # Initialize database before marking server ready
    if init_db:
        try:
            print("📊 Initializing database and tables...", flush=True)
            init_db()
        except Exception as e:
            print(f"⚠️ Warning: Database initialization failed: {e}", flush=True)
    
    print("✅ Application startup complete - server is ready!", flush=True)
    yield
    
    # Shutdown
    print("🛑 Shutting down E-commerce Store Backend...", flush=True)

# Middleware to ensure HTTPS redirects use HTTPS (for Cloud Run)
class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Check if request is behind a proxy (Cloud Run sets X-Forwarded-Proto)
        if request.headers.get("X-Forwarded-Proto") == "https":
            # Force the request URL to use HTTPS
            request.scope["scheme"] = "https"
        elif request.url.scheme == "http" and "X-Forwarded-Proto" in request.headers:
            # If behind proxy and X-Forwarded-Proto is set, use it
            proto = request.headers.get("X-Forwarded-Proto", "https")
            request.scope["scheme"] = proto
        
        response = await call_next(request)
        return response

# Create FastAPI app
app = FastAPI(
    title="E-commerce Store API",
    description="Full-stack e-commerce store backend API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add HTTPS redirect middleware FIRST (before CORS)
app.add_middleware(HTTPSRedirectMiddleware)

# Add CORS middleware - TEMPORARILY ALLOW ALL ORIGINS to fix CORS blocking
# This will be restricted later once we confirm everything works
print("🌐 Configuring CORS middleware - ALLOWING ALL ORIGINS (temporary)", flush=True)
print(f"🌐 CORS_ORIGINS env var: {os.getenv('CORS_ORIGINS', 'not set')}", flush=True)

try:
    # FORCE ALLOW ALL ORIGINS - this fixes the CORS blocking issue immediately
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins
        allow_credentials=False,  # Can't use credentials with wildcard (FastAPI requirement)
        allow_methods=["*"],  # Allow all HTTP methods
        allow_headers=["*"],  # Allow all headers
        expose_headers=["*"],  # Expose all headers
    )
    print("✅ CORS middleware configured - ALLOWING ALL ORIGINS", flush=True)
except Exception as e:
    print(f"❌ CRITICAL: CORS middleware setup failed: {e}", flush=True)
    import traceback
    traceback.print_exc()
    # Even if setup fails, try to add it anyway
    try:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        print("✅ CORS middleware added via fallback", flush=True)
    except Exception as e2:
        print(f"❌ CRITICAL: Even fallback CORS setup failed: {e2}", flush=True)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)

# Include routers individually - register each one separately so failures don't break others
router_configs = [
    ("auth", "/api/v1/auth", "Authentication"),
    ("products", "/api/v1/products", "Products"),
    ("cart", "/api/v1/cart", "Cart"),
    ("orders", "/api/v1/orders", "Orders"),
    ("admin", "/api/v1/admin", "Admin"),
    ("upload", "/api/v1/upload", "Upload"),
    ("favorites", "/api/v1/favorites", "Favorites"),
]

registered_count = 0
for router_name, prefix, tag in router_configs:
    if routers.get(router_name):
        try:
            app.include_router(routers[router_name], prefix=prefix, tags=[tag])
            print(f"✅ Router '{router_name}' registered at {prefix}", flush=True)
            registered_count += 1
        except Exception as e:
            print(f"⚠️ Warning: Failed to register router '{router_name}': {e}", flush=True)
            import traceback
            traceback.print_exc()
    else:
        print(f"⚠️ Warning: Router '{router_name}' not available, skipping", flush=True)

print(f"✅ Registered {registered_count}/{len(router_configs)} routers successfully", flush=True)

# Route to serve images from GCS for /uploads/{filename} requests
# This handles cases where products have relative /uploads/ URLs but files are in GCS
@app.get("/uploads/{filename:path}")
async def serve_upload_from_gcs(filename: str):
    """Serve uploaded images from GCS when requested via /uploads/ path"""
    try:
        GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "")
        if not GCS_BUCKET_NAME:
            # If GCS not configured, try local filesystem fallback
            file_path = os.path.join("uploads", filename)
            if os.path.exists(file_path):
                from fastapi.responses import FileResponse
                return FileResponse(file_path)
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Serve from GCS
        from google.cloud import storage
        from fastapi.responses import RedirectResponse
        
        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(f"uploads/{filename}")
        
        # Check if blob exists
        if not blob.exists():
            raise HTTPException(status_code=404, detail="Image not found in storage")
        
        # Try to get public URL first
        try:
            blob.reload()
            if blob.public_url:
                return RedirectResponse(url=blob.public_url, status_code=302)
        except:
            pass
        
        # If not public, generate signed URL
        from datetime import timedelta
        signed_url = blob.generate_signed_url(
            expiration=timedelta(days=365),
            method='GET'
        )
        return RedirectResponse(url=signed_url, status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error serving image from GCS: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to serve image: {str(e)}")

# Mount static files for uploads (fallback for local development)
if os.path.exists("uploads"):
    try:
        app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
    except Exception as e:
        print(f"⚠️ Warning: Could not mount static files: {e}", flush=True)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ecommerce-store-backend",
        "version": "1.0.0"
    }

@app.get("/health/live")
async def health_live():
    return {
        "status": "alive",
        "service": "ecommerce-store-backend",
        "version": "1.0.0"
    }

@app.get("/health/ready")
async def health_ready():
    return {
        "status": "ready",
        "service": "ecommerce-store-backend",
        "version": "1.0.0"
    }

# Database initialization endpoint
@app.get("/api/v1/init-db")
async def initialize_database():
    """Manually trigger database table creation and initialization"""
    try:
        from app.database import init_db, create_tables
        from app.database import engine
        
        if engine is None:
            raise HTTPException(status_code=500, detail="Database engine not available")
        
        # Create tables
        create_tables()
        
        # Initialize with sample data
        init_db()
        
        return {
            "status": "success",
            "message": "Database tables created and initialized successfully"
        }
    except Exception as e:
        import traceback
        error_msg = f"Database initialization failed: {str(e)}"
        print(f"❌ {error_msg}", flush=True)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)

# CORS test endpoint
@app.get("/api/v1/cors-test")
async def cors_test():
    """Test endpoint to verify CORS is working"""
    return {
        "status": "ok",
        "message": "CORS is configured correctly",
        "allowed_origins": getattr(settings, 'allowed_origins', [])
    }

# API version endpoint
@app.get("/api/version")
async def api_version():
    return {
        "api_version": "v1",
        "current_version": "1.0.0",
        "supported_versions": ["v1"],
        "deprecated_versions": []
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to E-commerce Store API",
        "version": "1.0.0",
        "api_version": "v1",
        "docs": "/docs",
        "health": "/health",
        "version_info": "/api/version"
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

