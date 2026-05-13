import sys
import importlib

# Force reload
if 'app.services.local_knowledge_service' in sys.modules:
    del sys.modules['app.services.local_knowledge_service']

from app.services.local_knowledge_service import LocalKnowledgeService

s = LocalKnowledgeService()
print(f"Type: {type(s.knowledge_base)}")
print(f"Length: {len(s.knowledge_base)}")
print(f"Has _initialize_knowledge_base: {hasattr(s, '_initialize_knowledge_base')}")
print(f"Calling _initialize_knowledge_base directly...")
kb = s._initialize_knowledge_base()
print(f"Direct call type: {type(kb)}")
print(f"Direct call length: {len(kb)}")
