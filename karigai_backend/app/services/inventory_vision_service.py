"""
Inventory Vision Service

This service provides automated stock counting from shelf images,
product categorization, and restocking list generation.
"""

import os
from typing import List, Optional, Dict, Any
import json

from app.core.vision_engine import (
    VisionEngine,
    ImageData,
    EquipmentInfo,
    ErrorCode,
    PatternAnalysis,
    QualityAssessment,
    ProductType,
    InventoryItem,
    TroubleshootingStep,
    VisionProcessingError
)


class InventoryVisionService(VisionEngine):
    """
    Inventory snapshot management service for automated stock counting.
    
    This service:
    1. Identifies and counts visible items on shelves
    2. Categorizes products by type and brand
    3. Generates restocking lists with current quantities
    4. Considers historical usage patterns for suggestions
    5. Integrates with inventory management systems
    """
    
    def __init__(self, api_key: Optional[str] = None, use_google_vision: bool = False):
        """
        Initialize inventory vision service.
        
        Args:
            api_key: OpenAI or Google Cloud API key
            use_google_vision: If True, use Google Vision API
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.use_google_vision = use_google_vision
        
        if use_google_vision:
            self.google_api_key = api_key or os.getenv("GOOGLE_CLOUD_API_KEY")
        
        # Product database for common inventory items
        self.product_database = self._load_product_database()
        
        # Historical usage patterns (simplified)
        self.usage_patterns = {}
    
    def _load_product_database(self) -> Dict[str, Dict[str, Any]]:
        """Load product database with common inventory items."""
        return {
            "automotive": {
                "motor_oil": {
                    "brands": ["Castrol", "Mobil", "Shell", "Valvoline"],
                    "typical_shelf_life": 365,
                    "reorder_threshold": 5
                },
                "air_filter": {
                    "brands": ["Bosch", "Mann", "K&N", "Fram"],
                    "typical_shelf_life": 730,
                    "reorder_threshold": 3
                },
                "spark_plug": {
                    "brands": ["NGK", "Bosch", "Denso", "Champion"],
                    "typical_shelf_life": 1825,
                    "reorder_threshold": 10
                },
                "brake_pad": {
                    "brands": ["Brembo", "Bosch", "ATE", "TRW"],
                    "typical_shelf_life": 1095,
                    "reorder_threshold": 4
                }
            },
            "hardware": {
                "screws": {
                    "types": ["Wood screws", "Machine screws", "Self-tapping"],
                    "reorder_threshold": 50
                },
                "nails": {
                    "types": ["Common nails", "Finishing nails", "Roofing nails"],
                    "reorder_threshold": 100
                },
                "bolts": {
                    "types": ["Hex bolts", "Carriage bolts", "Eye bolts"],
                    "reorder_threshold": 30
                }
            },
            "electronics": {
                "batteries": {
                    "types": ["AA", "AAA", "9V", "CR2032"],
                    "brands": ["Duracell", "Energizer", "Panasonic"],
                    "reorder_threshold": 20
                },
                "cables": {
                    "types": ["USB-C", "HDMI", "Power cables"],
                    "reorder_threshold": 10
                }
            },
            "general": {
                "unknown_item": {
                    "reorder_threshold": 5
                }
            }
        }
    
    async def count_inventory(self, image: ImageData) -> List[InventoryItem]:
        """
        Count and identify items in inventory snapshot.
        
        Args:
            image: ImageData containing shelf/inventory photo
            
        Returns:
            List of InventoryItem objects with counts
        """
        try:
            if self.use_google_vision:
                return await self._count_inventory_google(image)
            else:
                return await self._count_inventory_openai(image)
        except Exception as e:
            raise VisionProcessingError(
                f"Inventory counting failed: {str(e)}",
                original_error=e
            )
    
    async def _count_inventory_openai(self, image: ImageData) -> List[InventoryItem]:
        """Count inventory using OpenAI GPT-4V."""
        try:
            import openai
            
            if not self.api_key:
                raise VisionProcessingError("OpenAI API key not configured")
            
            client = openai.OpenAI(api_key=self.api_key)
            base64_image = image.to_base64()
            
            prompt = """Analyze this shelf/inventory image and identify all visible products. For each product, provide:
1. Product name/type
2. Brand (if visible)
3. Quantity/count
4. Location on shelf (e.g., "Top shelf, left side")
5. Category (automotive, hardware, electronics, etc.)

Respond in JSON format:
{
    "items": [
        {
            "name": "product name",
            "brand": "brand name or null",
            "quantity": number,
            "location": "shelf location",
            "category": "category"
        }
    ]
}"""
            
            response = client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{image.format.value};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            # Convert to InventoryItem objects
            inventory_items = []
            for idx, item in enumerate(result.get("items", [])):
                inventory_items.append(InventoryItem(
                    item_id=f"item_{hash(item['name'] + str(idx)) % 100000}",
                    name=item.get("name", "Unknown"),
                    brand=item.get("brand"),
                    category=item.get("category"),
                    quantity=item.get("quantity", 0),
                    location=item.get("location"),
                    confidence_score=0.85
                ))
            
            return inventory_items
            
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return self._create_fallback_inventory()
        except Exception as e:
            raise VisionProcessingError(
                f"OpenAI inventory counting failed: {str(e)}",
                original_error=e
            )
    
    async def _count_inventory_google(self, image: ImageData) -> List[InventoryItem]:
        """Count inventory using Google Vision API."""
        try:
            from google.cloud import vision
            
            if not self.google_api_key:
                raise VisionProcessingError("Google Cloud API key not configured")
            
            client = vision.ImageAnnotatorClient()
            vision_image = vision.Image(content=image.image_bytes)
            
            # Perform object detection
            response = client.object_localization(image=vision_image)
            objects = response.localized_object_annotations
            
            # Perform label detection for categories
            label_response = client.label_detection(image=vision_image)
            labels = label_response.label_annotations
            
            # Group objects by name and count
            object_counts = {}
            for obj in objects:
                name = obj.name
                if name in object_counts:
                    object_counts[name]["count"] += 1
                else:
                    object_counts[name] = {
                        "count": 1,
                        "confidence": obj.score,
                        "locations": []
                    }
                
                # Store location
                vertices = obj.bounding_poly.normalized_vertices
                location = f"Position ({vertices[0].x:.2f}, {vertices[0].y:.2f})"
                object_counts[name]["locations"].append(location)
            
            # Determine category from labels
            category = "general"
            if labels:
                category = labels[0].description.lower()
            
            # Convert to InventoryItem objects
            inventory_items = []
            for idx, (name, data) in enumerate(object_counts.items()):
                inventory_items.append(InventoryItem(
                    item_id=f"item_{hash(name + str(idx)) % 100000}",
                    name=name,
                    brand=None,
                    category=category,
                    quantity=data["count"],
                    location=data["locations"][0] if data["locations"] else None,
                    confidence_score=data["confidence"]
                ))
            
            return inventory_items
            
        except Exception as e:
            raise VisionProcessingError(
                f"Google Vision inventory counting failed: {str(e)}",
                original_error=e
            )
    
    def _create_fallback_inventory(self) -> List[InventoryItem]:
        """Create fallback inventory when AI fails."""
        return [
            InventoryItem(
                item_id="item_unknown",
                name="Unknown items detected",
                quantity=0,
                confidence_score=0.3
            )
        ]
    
    def generate_restocking_list(
        self,
        current_inventory: List[InventoryItem],
        historical_usage: Optional[Dict[str, int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate restocking list based on current inventory and usage patterns.
        
        Args:
            current_inventory: List of current inventory items
            historical_usage: Optional dict of item_name -> monthly_usage
            
        Returns:
            List of items needing restocking with suggested quantities
        """
        restocking_list = []
        
        for item in current_inventory:
            # Get reorder threshold for this item
            threshold = self._get_reorder_threshold(item.name, item.category)
            
            # Check if below threshold
            if item.quantity <= threshold:
                # Calculate suggested reorder quantity
                monthly_usage = historical_usage.get(item.name, 10) if historical_usage else 10
                suggested_quantity = max(monthly_usage * 2, threshold * 2)
                
                restocking_list.append({
                    "item_id": item.item_id,
                    "name": item.name,
                    "brand": item.brand,
                    "category": item.category,
                    "current_quantity": item.quantity,
                    "reorder_threshold": threshold,
                    "suggested_quantity": suggested_quantity,
                    "priority": "High" if item.quantity == 0 else "Medium" if item.quantity < threshold / 2 else "Low"
                })
        
        # Sort by priority
        priority_order = {"High": 0, "Medium": 1, "Low": 2}
        restocking_list.sort(key=lambda x: priority_order[x["priority"]])
        
        return restocking_list
    
    def _get_reorder_threshold(self, item_name: str, category: Optional[str]) -> int:
        """Get reorder threshold for an item."""
        # Try to find in product database
        if category:
            category_lower = category.lower()
            for cat_key, products in self.product_database.items():
                if cat_key in category_lower or category_lower in cat_key:
                    for product_key, product_data in products.items():
                        if product_key in item_name.lower() or item_name.lower() in product_key:
                            return product_data.get("reorder_threshold", 5)
        
        # Default threshold
        return 5
    
    def categorize_products(self, items: List[InventoryItem]) -> Dict[str, List[InventoryItem]]:
        """Categorize products by type and brand."""
        categorized = {}
        
        for item in items:
            category = item.category or "uncategorized"
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(item)
        
        return categorized
    
    # Implement remaining abstract methods
    
    async def identify_equipment(self, image: ImageData) -> EquipmentInfo:
        """Not implemented in inventory service."""
        return EquipmentInfo(
            equipment_id="not_implemented",
            brand="N/A",
            model="N/A",
            category="N/A",
            confidence_score=0.0
        )
    
    async def detect_error_codes(self, image: ImageData) -> List[ErrorCode]:
        """Not implemented in inventory service."""
        return []
    
    async def analyze_pattern(self, image: ImageData) -> PatternAnalysis:
        """Not implemented in inventory service."""
        return PatternAnalysis(pattern_type="Not implemented", confidence_score=0.0)
    
    async def assess_quality(self, image: ImageData, product_type: ProductType) -> QualityAssessment:
        """Not implemented in inventory service."""
        return QualityAssessment(grade="N/A", score=0.0, confidence_score=0.0)
    
    async def extract_text(self, image: ImageData, language_code: str) -> str:
        """Basic text extraction."""
        return "Text extraction not primary function of inventory service"
    
    async def preprocess_image(self, image: ImageData, **kwargs) -> ImageData:
        """Basic image preprocessing."""
        return ImageData(
            image_bytes=image.image_bytes,
            width=image.width,
            height=image.height,
            format=image.format,
            file_path=image.file_path,
            file_size=image.file_size,
            preprocessed=True,
            metadata=image.metadata
        )
