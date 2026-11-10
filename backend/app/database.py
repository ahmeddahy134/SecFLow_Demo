from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models import Base
import os

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/ecommerce")
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# Create engine with connection pool settings for Cloud Run
# Use echo=False to avoid logging all SQL queries
# Set pool_pre_ping to verify connections before using
# IMPORTANT: Don't connect immediately - use pool_pre_ping to verify on first use
try:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=300,    # Recycle connections after 5 minutes
        connect_args={"connect_timeout": 5},  # 5 second connection timeout (reduced from 10)
        echo=False,  # Don't echo SQL queries
        pool_size=5,  # Limit pool size
        max_overflow=10  # Limit overflow connections
    )
    print("✅ Database engine created (connection will be tested on first use)", flush=True)
except Exception as e:
    print(f"⚠️ Warning: Could not create database engine: {e}", flush=True)
    engine = None

# Create session factory (only if engine exists)
if engine:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    SessionLocal = None

def get_db():
    """Dependency to get database session"""
    if engine is None:
        error_msg = "Database not configured. Please set DATABASE_URL environment variable."
        print(f"❌ {error_msg}", flush=True)
        raise Exception(error_msg)
    
    try:
        db = SessionLocal()
        # Test the connection
        db.execute(text("SELECT 1"))
    except Exception as e:
        error_msg = f"Database connection failed: {str(e)}"
        print(f"❌ {error_msg}", flush=True)
        import traceback
        traceback.print_exc()
        raise Exception(error_msg)
    
    try:
        yield db
    except Exception as e:
        print(f"❌ Database session error: {str(e)}", flush=True)
        db.rollback()
        raise
    finally:
        db.close()

def create_tables():
    """Create all tables"""
    if engine is None:
        print("⚠️ Warning: Database engine not available, skipping table creation", flush=True)
        return
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully", flush=True)
    except Exception as e:
        print(f"⚠️ Warning: Could not create tables: {e}", flush=True)
        # Don't raise - allow app to start without database

def init_db():
    """Initialize database with sample data - non-blocking"""
    if engine is None or SessionLocal is None:
        print("⚠️ Warning: Database not configured, skipping initialization", flush=True)
        return
    
    try:
        create_tables()
    except Exception as e:
        print(f"⚠️ Warning: Table creation failed: {e}", flush=True)
        return  # Don't block startup
    
    try:
        # Import here to avoid circular imports
        from app.routers.products import mock_products
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        db = SessionLocal()
        
        try:
            # Check if data already exists
            from app.models import Product, User
            
            if db.query(Product).count() == 0:
                # Add sample products
                for product_data in mock_products:
                    product = Product(
                        id=product_data["id"],
                        name=product_data["name"],
                        description=product_data["description"],
                        price=product_data["price"],
                        category=product_data["category"],
                        image_url=product_data["image_url"],
                        stock=product_data["stock"],
                        rating=product_data["rating"]
                    )
                    db.add(product)
            
            if db.query(User).count() == 0:
                # Add sample users with hashed passwords read from environment
                admin_pw = os.getenv("DEMO_ADMIN_PASSWORD", "admin123")
                user_pw = os.getenv("DEMO_USER_PASSWORD", "password")
                sample_users = [
                    {
                        "id": "admin_1",
                        "email": "admin@ecommerce.com",
                        "name": "Admin User",
                        "password": admin_pw,
                        "role": "admin"
                    },
                    {
                        "id": "user_1", 
                        "email": "test@example.com",
                        "name": "Test User",
                        "password": user_pw,
                        "role": "customer"
                    }
                ]
                
                for user_data in sample_users:
                    try:
                        # Ensure password is a string
                        password_str = str(user_data["password"])
                        # Truncate to 72 bytes if needed (bcrypt limit)
                        # Convert to bytes, truncate, then back to string
                        password_bytes = password_str.encode('utf-8')
                        if len(password_bytes) > 72:
                            password_bytes = password_bytes[:72]
                            password_str = password_bytes.decode('utf-8', errors='ignore')
                        
                        # Hash the password - ensure it's not longer than 72 bytes
                        # Double-check byte length before hashing
                        password_bytes_check = password_str.encode('utf-8')
                        if len(password_bytes_check) > 72:
                            password_str = password_bytes_check[:72].decode('utf-8', errors='ignore')
                        
                        # Hash the password
                        password_hash = pwd_context.hash(password_str)
                        
                        user = User(
                            id=user_data["id"],
                            email=user_data["email"],
                            name=user_data["name"],
                            password_hash=password_hash,
                            role=user_data["role"]
                        )
                        db.add(user)
                        print(f"✅ User '{user_data['email']}' added.", flush=True)
                    except ValueError as ve:
                        # Handle bcrypt password length error specifically
                        if "password cannot be longer than 72 bytes" in str(ve):
                            print(f"⚠️ Password for {user_data['email']} too long, skipping...", flush=True)
                        else:
                            print(f"❌ Error adding user '{user_data['email']}': {ve}", flush=True)
                            import traceback
                            traceback.print_exc()
                        # Continue with next user
                        continue
                    except Exception as e:
                        print(f"❌ Error adding user '{user_data['email']}': {e}", flush=True)
                        import traceback
                        traceback.print_exc()
                        # Continue with next user
                        continue
            
            db.commit()
            print("✅ Database initialized with sample data", flush=True)
            
        except Exception as e:
            print(f"❌ Error initializing database: {e}", flush=True)
            import traceback
            traceback.print_exc()
            db.rollback()
        finally:
            db.close()
    except Exception as e:
        print(f"⚠️ Warning: Database initialization failed: {e}", flush=True)
        import traceback
        traceback.print_exc()
        # Don't raise - allow app to start
