from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
from passlib.context import CryptContext
from app.routers.auth import verify_token
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Order as OrderModel, OrderItem as OrderItemModel, Product as ProductModel, User as UserModel

router = APIRouter()

# Pydantic models
class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    category: str
    image_url: str
    stock: int

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    stock: Optional[int] = None

class OrderStatusUpdate(BaseModel):
    status: str

class AdminStats(BaseModel):
    total_products: int
    total_orders: int
    total_revenue: float
    pending_orders: int
    low_stock_products: int

# Import real product data
from app.routers.products import mock_products
from app.routers.orders import orders_db

# Initialize admin data with real products
admin_products = mock_products.copy()

def check_admin_role(user_id: str, db: Session) -> bool:
    """Check if user has admin role"""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    return user and user.role == "admin"

# Import the shared normalization function from products router
from app.routers.products import _normalize_image_url

@router.get("/stats", response_model=AdminStats)
async def get_admin_stats(current_user_id: str = Depends(verify_token), db: Session = Depends(get_db)):
    """Get admin dashboard statistics"""
    if not check_admin_role(current_user_id, db):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Get real stats from database
        total_products = db.query(ProductModel).count()
        total_orders = db.query(OrderModel).count()
        total_revenue = db.query(OrderModel).with_entities(OrderModel.total).all()
        total_revenue = sum([order.total for order in total_revenue]) if total_revenue else 0
        pending_orders = db.query(OrderModel).filter(OrderModel.status == "pending").count()
        low_stock_products = db.query(ProductModel).filter(ProductModel.stock < 10).count()
        
        stats = AdminStats(
            total_products=total_products,
            total_orders=total_orders,
            total_revenue=total_revenue,
            pending_orders=pending_orders,
            low_stock_products=low_stock_products
        )
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Product Management
@router.post("/products", response_model=dict)
async def create_product(
    product: ProductCreate,
    current_user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Create a new product"""
    if not check_admin_role(current_user_id, db):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Generate unique product ID
        product_id = f"prod_{int(datetime.now().timestamp())}"
        
        # Create product in database
        db_product = ProductModel(
            id=product_id,
            name=product.name,
            description=product.description,
            price=product.price,
            category=product.category,
            image_url=product.image_url,
            stock=product.stock,
            rating=0.0
        )
        
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        
        return {"message": "Product created successfully", "product_id": product_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/products", response_model=List[dict])
async def get_admin_products(
    request: Request,
    current_user_id: str = Depends(verify_token),
    page: int = 1,
    limit: int = 1000,  # Increased default limit to 1000 to show all products
    db: Session = Depends(get_db)
):
    """Get all products for admin management"""
    if not check_admin_role(current_user_id, db):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Get products from database
        # If limit is very high (>= 1000), fetch all products without pagination
        if limit >= 1000:
            db_products = db.query(ProductModel).order_by(ProductModel.created_at.desc()).all()
        else:
            offset = (page - 1) * limit
            db_products = db.query(ProductModel).order_by(ProductModel.created_at.desc()).offset(offset).limit(limit).all()
        
        # Convert to admin format
        products = []
        for db_product in db_products:
            product = {
                "id": db_product.id,
                "name": db_product.name,
                "description": db_product.description,
                "price": db_product.price,
                "category": db_product.category,
                "image_url": _normalize_image_url(db_product.image_url, request),
                "stock": db_product.stock,
                "rating": db_product.rating,
                "created_at": db_product.created_at.isoformat(),
                "updated_at": db_product.updated_at.isoformat()
            }
            products.append(product)
        
        return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/products/{product_id}")
async def update_product(
    product_id: str,
    product_update: ProductUpdate,
    current_user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Update product information"""
    if not check_admin_role(current_user_id, db):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Find product in database
        db_product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
        if not db_product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Update fields
        update_data = product_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_product, field, value)
        
        db_product.updated_at = datetime.now()
        db.commit()
        db.refresh(db_product)
        
        return {"message": "Product updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/products/{product_id}")
async def delete_product(
    product_id: str,
    current_user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Delete a product"""
    if not check_admin_role(current_user_id, db):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Find product in database
        db_product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
        if not db_product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Delete product
        db.delete(db_product)
        db.commit()
        
        return {"message": "Product deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Order Management
@router.get("/orders", response_model=List[dict])
async def get_admin_orders(
    current_user_id: str = Depends(verify_token),
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all orders for admin management"""
    if not check_admin_role(current_user_id, db):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Get orders from database
        query = db.query(OrderModel)
        if status:
            query = query.filter(OrderModel.status == status)
        
        orders = query.offset((page - 1) * limit).limit(limit).all()
        
        # Convert orders to admin format
        admin_orders_list = []
        for order in orders:
            # Get user info for the order
            user = db.query(UserModel).filter(UserModel.id == order.user_id).first()
            
            # Get order items with product details
            order_items = db.query(OrderItemModel).filter(OrderItemModel.order_id == order.id).all()
            
            # Get product details for each item
            items_with_details = []
            for item in order_items:
                product = db.query(ProductModel).filter(ProductModel.id == item.product_id).first()
                items_with_details.append({
                    "product_id": item.product_id,
                    "name": item.name,
                    "quantity": item.quantity,
                    "price": item.price,
                    "subtotal": item.price * item.quantity,
                    "image_url": product.image_url if product else None
                })
            
            admin_order = {
                "id": order.id,
                "user_id": order.user_id,
                "user_email": user.email if user else "Unknown",
                "user_name": user.name if user else "Unknown User",
                "items": items_with_details,
                "total": order.total,
                "subtotal": order.subtotal,
                "tax": order.tax,
                "shipping": order.shipping,
                "status": order.status,
                "shipping_address": order.shipping_address,
                "notes": order.shipping_address,  # Using shipping_address as notes for now
                "created_at": order.created_at.isoformat(),
                "updated_at": order.updated_at.isoformat()
            }
            admin_orders_list.append(admin_order)
        
        return admin_orders_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class OrderUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None

@router.put("/orders/{order_id}")
async def update_order(
    order_id: str,
    order_update: OrderUpdate,
    current_user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Update order details"""
    if not check_admin_role(current_user_id, db):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Get order from database
        order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Update order fields
        update_data = order_update.dict(exclude_unset=True)
        if "status" in update_data:
            order.status = update_data["status"]
        if "notes" in update_data:
            # Store notes in shipping_address field for now (could add notes field to model later)
            order.shipping_address = update_data["notes"]
        
        order.updated_at = datetime.now()
        
        db.commit()
        db.refresh(order)
        
        return {"message": "Order updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        error_detail = f"Failed to update order: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Error in update_order: {error_detail}", flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to update order: {str(e)}")

@router.get("/orders/{order_id}")
async def get_admin_order(
    order_id: str,
    current_user_id: str = Depends(verify_token)
):
    """Get specific order details for admin"""
    if not check_admin_role(current_user_id):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        order = next((o for o in admin_orders if o["id"] == order_id), None)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        return order
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)

@router.post("/init-database")
async def initialize_database(db: Session = Depends(get_db)):
    """Initialize database with admin user and sample products"""
    try:
        # Check if admin user already exists
        existing_admin = db.query(UserModel).filter(UserModel.email == "admin@example.com").first()
        if existing_admin:
            return {"message": "Database already initialized", "admin_exists": True}
        
        # Create admin user
        admin_user = UserModel(
            id=str(uuid.uuid4()),
            email="admin@example.com",
            name="Admin User",
            password_hash=hash_password("admin123"),
            role="admin",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(admin_user)
        
        # Create sample products
        sample_products = [
            ProductModel(
                id=str(uuid.uuid4()),
                name="Wireless Headphones",
                description="High-quality wireless headphones with noise cancellation",
                price=99.99,
                category="Electronics",
                image_url="https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500",
                stock=50,
                rating=4.5,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            ProductModel(
                id=str(uuid.uuid4()),
                name="Smart Watch",
                description="Fitness tracking smartwatch with heart rate monitor",
                price=199.99,
                category="Electronics",
                image_url="https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500",
                stock=30,
                rating=4.2,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            ProductModel(
                id=str(uuid.uuid4()),
                name="Canvas Backpack",
                description="Durable canvas backpack for travel and daily adventures",
                price=45.99,
                category="Clothing",
                image_url="https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=500",
                stock=25,
                rating=4.0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            ProductModel(
                id=str(uuid.uuid4()),
                name="Running Shoes",
                description="Comfortable running shoes with excellent cushioning",
                price=129.99,
                category="Sports",
                image_url="https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500",
                stock=40,
                rating=4.3,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            ProductModel(
                id=str(uuid.uuid4()),
                name="Coffee Maker",
                description="Automatic coffee maker with programmable features",
                price=79.99,
                category="Home & Garden",
                image_url="https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=500",
                stock=15,
                rating=4.1,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            ProductModel(
                id=str(uuid.uuid4()),
                name="Bluetooth Speaker",
                description="Portable Bluetooth speaker with 360-degree sound",
                price=59.99,
                category="Electronics",
                image_url="https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=500",
                stock=35,
                rating=4.4,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            ProductModel(
                id=str(uuid.uuid4()),
                name="Yoga Mat",
                description="Non-slip yoga mat for home workouts",
                price=29.99,
                category="Sports",
                image_url="https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=500",
                stock=60,
                rating=4.0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            ProductModel(
                id=str(uuid.uuid4()),
                name="Laptop Stand",
                description="Adjustable laptop stand for better ergonomics",
                price=39.99,
                category="Electronics",
                image_url="https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=500",
                stock=20,
                rating=4.2,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ]
        
        for product in sample_products:
            db.add(product)
        
        # Commit all changes
        db.commit()
        
        return {
            "message": "Database initialized successfully",
            "admin_created": True,
            "products_created": len(sample_products)
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to initialize database: {str(e)}")



