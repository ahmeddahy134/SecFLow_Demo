from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from app.routers.auth import verify_token
from app.database import get_db
from app.models import Product
from sqlalchemy.orm import Session

router = APIRouter()

# Pydantic models
class CartItem(BaseModel):
    product_id: str
    name: str
    price: float
    quantity: int
    subtotal: float
    image_url: Optional[str] = None

class CartResponse(BaseModel):
    items: List[CartItem]
    total_items: int
    subtotal: float
    tax: float
    shipping: float
    total: float

class AddToCartRequest(BaseModel):
    product_id: str
    quantity: int = 1

class UpdateCartItemRequest(BaseModel):
    quantity: int

# Mock cart storage
carts_db = {}

def get_user_cart(user_id: str):
    if user_id not in carts_db:
        carts_db[user_id] = {"items": {}, "total_items": 0, "subtotal": 0}
    
    # Calculate totals
    cart = carts_db[user_id]
    cart["total_items"] = sum(item["quantity"] for item in cart["items"].values())
    cart["subtotal"] = sum(item["subtotal"] for item in cart["items"].values())
    
    return cart

@router.get("/", response_model=CartResponse)
async def get_cart(current_user_id: str = Depends(verify_token)):
    """Get user's shopping cart"""
    cart = get_user_cart(current_user_id)
    return CartResponse(
        items=list(cart["items"].values()),
        total_items=cart["total_items"],
        subtotal=cart["subtotal"],
        tax=cart["subtotal"] * 0.08,
        shipping=0 if cart["subtotal"] >= 50 else 5.99,
        total=cart["subtotal"] * 1.08 + (0 if cart["subtotal"] >= 50 else 5.99)
    )

@router.post("/add", response_model=CartResponse)
async def add_to_cart(request: AddToCartRequest, current_user_id: str = Depends(verify_token), db: Session = Depends(get_db)):
    """Add item to cart"""
    cart = get_user_cart(current_user_id)
    
    # Get real product data from database
    try:
        product = db.query(Product).filter(Product.id == request.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        product_data = {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "image_url": product.image_url
        }
    except Exception as e:
        # Fallback to mock data if product not found
        product_data = {
            "id": request.product_id,
            "name": f"Product {request.product_id}",
            "price": 29.99,
            "image_url": None
        }
    
    if request.product_id in cart["items"]:
        cart["items"][request.product_id]["quantity"] += request.quantity
        cart["items"][request.product_id]["subtotal"] = cart["items"][request.product_id]["price"] * cart["items"][request.product_id]["quantity"]
    else:
        cart["items"][request.product_id] = {
            "product_id": request.product_id,
            "name": product_data["name"],
            "price": product_data["price"],
            "quantity": request.quantity,
            "subtotal": product_data["price"] * request.quantity,
            "image_url": product_data.get("image_url", None)
        }
    
    cart = get_user_cart(current_user_id)
    return CartResponse(
        items=list(cart["items"].values()),
        total_items=cart["total_items"],
        subtotal=cart["subtotal"],
        tax=cart["subtotal"] * 0.08,
        shipping=0 if cart["subtotal"] >= 50 else 5.99,
        total=cart["subtotal"] * 1.08 + (0 if cart["subtotal"] >= 50 else 5.99)
    )

@router.delete("/items/{product_id}")
async def remove_cart_item(product_id: str, current_user_id: str = Depends(verify_token)):
    """Remove item from cart"""
    cart = get_user_cart(current_user_id)
    if product_id in cart["items"]:
        del cart["items"][product_id]
    return {"message": "Item removed"}

@router.put("/items/{product_id}")
async def update_cart_item(product_id: str, request: UpdateCartItemRequest, current_user_id: str = Depends(verify_token)):
    """Update cart item quantity"""
    cart = get_user_cart(current_user_id)
    if product_id not in cart["items"]:
        raise HTTPException(status_code=404, detail="Item not found in cart")
    
    cart["items"][product_id]["quantity"] = request.quantity
    cart["items"][product_id]["subtotal"] = cart["items"][product_id]["price"] * request.quantity
    
    cart = get_user_cart(current_user_id)
    return CartResponse(
        items=list(cart["items"].values()),
        total_items=cart["total_items"],
        subtotal=cart["subtotal"],
        tax=cart["subtotal"] * 0.08,
        shipping=0 if cart["subtotal"] >= 50 else 5.99,
        total=cart["subtotal"] * 1.08 + (0 if cart["subtotal"] >= 50 else 5.99)
    )

@router.delete("/")
async def clear_cart(current_user_id: str = Depends(verify_token)):
    """Clear user's shopping cart"""
    cart = get_user_cart(current_user_id)
    cart["items"] = {}
    cart["total_items"] = 0
    cart["subtotal"] = 0
    return {"message": "Cart cleared"}
