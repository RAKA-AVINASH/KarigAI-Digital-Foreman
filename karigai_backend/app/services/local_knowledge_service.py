from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class KnowledgeCategory(Enum):
    PLANTS = 'plants'
    ATTRACTIONS = 'attractions'
    WILDLIFE = 'wildlife'
    CULTURE = 'culture'
    CUISINE = 'cuisine'
    ACTIVITIES = 'activities'

@dataclass
class KnowledgeItem:
    item_id: str
    name: str
    category: KnowledgeCategory
    description: str
    location: str
    local_name: Optional[str] = None
    seasonal_info: Optional[str] = None
    cultural_significance: Optional[str] = None
    practical_info: Optional[str] = None

@dataclass
class QueryResult:
    items: List[KnowledgeItem]
    query: str
    location: str
    total_results: int

class LocalKnowledgeService:
    def __init__(self):
        self.knowledge_base = self._initialize_knowledge_base()
        self.location_index = self._build_location_index()
    
    def query_plants(self, query: str, location: str) -> QueryResult:
        return self._query_by_category(query, location, KnowledgeCategory.PLANTS)
    
    def query_attractions(self, query: str, location: str) -> QueryResult:
        return self._query_by_category(query, location, KnowledgeCategory.ATTRACTIONS)
    
    def query_wildlife(self, query: str, location: str) -> QueryResult:
        return self._query_by_category(query, location, KnowledgeCategory.WILDLIFE)
    
    def get_location_highlights(self, location: str, limit: int = 5) -> List[KnowledgeItem]:
        location_items = self.location_index.get(location.lower(), [])
        priority_categories = [KnowledgeCategory.ATTRACTIONS, KnowledgeCategory.CULTURE, KnowledgeCategory.ACTIVITIES]
        highlights = []
        for item_id in location_items:
            if len(highlights) >= limit:
                break
            item = self.knowledge_base.get(item_id)
            if item and item.category in priority_categories:
                highlights.append(item)
        for item_id in location_items:
            if len(highlights) >= limit:
                break
            item = self.knowledge_base.get(item_id)
            if item and item not in highlights:
                highlights.append(item)
        return highlights[:limit]
    
    def generate_promotional_content(self, location: str, property_name: str, target_audience: str = 'general') -> str:
        highlights = self.get_location_highlights(location, limit=3)
        if not highlights:
            return f'Welcome to {property_name} in {location}. Experience the beauty and culture of this unique destination.'
        intro = f'Discover {location} at {property_name}\n\n'
        features = []
        for item in highlights:
            if item.category == KnowledgeCategory.ATTRACTIONS:
                features.append(f'• Visit {item.name}: {item.description}')
            elif item.category == KnowledgeCategory.PLANTS:
                features.append(f'• Explore {item.name}: {item.description}')
            elif item.category == KnowledgeCategory.CULTURE:
                features.append(f'• Experience {item.name}: {item.description}')
            else:
                features.append(f'• Enjoy {item.name}: {item.description}')
        content = intro + '\n'.join(features)
        content += f'\n\nBook your stay at {property_name} and immerse yourself in the local experience.'
        return content
    
    def get_detailed_information(self, item_id: str) -> Optional[KnowledgeItem]:
        return self.knowledge_base.get(item_id)
    
    def search_by_name(self, name: str, location: Optional[str] = None) -> List[KnowledgeItem]:
        results = []
        name_lower = name.lower()
        for item in self.knowledge_base.values():
            name_match = name_lower in item.name.lower() or (item.local_name and name_lower in item.local_name.lower())
            location_match = location is None or location.lower() in item.location.lower()
            if name_match and location_match:
                results.append(item)
        return results
    
    def _query_by_category(self, query: str, location: str, category: KnowledgeCategory) -> QueryResult:
        query_lower = query.lower()
        location_lower = location.lower()
        matching_items = []
        for item in self.knowledge_base.values():
            if item.category != category:
                continue
            if location_lower not in item.location.lower():
                continue
            if (query_lower in item.name.lower() or query_lower in item.description.lower() or 
                (item.local_name and query_lower in item.local_name.lower())):
                matching_items.append(item)
        return QueryResult(items=matching_items, query=query, location=location, total_results=len(matching_items))
    
    def _initialize_knowledge_base(self) -> Dict[str, KnowledgeItem]:
        items = [
            KnowledgeItem(item_id='plant_001', name='Saffron Crocus', category=KnowledgeCategory.PLANTS,
                description='The precious saffron flower that blooms in autumn', location='Kashmir', local_name='Kong'),
            KnowledgeItem(item_id='plant_002', name='Chinar Tree', category=KnowledgeCategory.PLANTS,
                description='Majestic maple tree with large leaves', location='Kashmir', local_name='Bouin'),
            KnowledgeItem(item_id='attr_001', name='Dal Lake', category=KnowledgeCategory.ATTRACTIONS,
                description='Iconic lake with houseboats and shikaras', location='Kashmir', local_name='Dal'),
            KnowledgeItem(item_id='attr_002', name='Gulmarg', category=KnowledgeCategory.ATTRACTIONS,
                description='Meadow of flowers and premier ski resort', location='Kashmir'),
            KnowledgeItem(item_id='plant_003', name='Khejri Tree', category=KnowledgeCategory.PLANTS,
                description='Desert tree sacred to Bishnoi community', location='Rajasthan', local_name='Khejri'),
            KnowledgeItem(item_id='attr_003', name='Amber Fort', category=KnowledgeCategory.ATTRACTIONS,
                description='Magnificent hilltop fort', location='Jaipur', local_name='Amer Qila'),
            KnowledgeItem(item_id='cult_001', name='Kathakali Dance', category=KnowledgeCategory.CULTURE,
                description='Classical dance-drama', location='Kerala', local_name='Kathakali'),
            KnowledgeItem(item_id='cuis_001', name='Kerala Sadya', category=KnowledgeCategory.CUISINE,
                description='Traditional vegetarian feast', location='Kerala', local_name='Sadya')
        ]
        return {item.item_id: item for item in items}
    
    def _build_location_index(self) -> Dict[str, List[str]]:
        index = {}
        for item_id, item in self.knowledge_base.items():
            location_key = item.location.lower()
            if location_key not in index:
                index[location_key] = []
            index[location_key].append(item_id)
        return index
    
    def get_all_locations(self) -> List[str]:
        return list(self.location_index.keys())
    
    def get_categories(self) -> List[str]:
        return [cat.value for cat in KnowledgeCategory]
