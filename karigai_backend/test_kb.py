from app.services.local_knowledge_service import LocalKnowledgeService

s = LocalKnowledgeService()
print(f"Type: {type(s.knowledge_base)}")
print(f"Length: {len(s.knowledge_base)}")
if hasattr(s.knowledge_base, 'keys'):
    print(f"Keys: {list(s.knowledge_base.keys())[:3]}")
else:
    print("No keys method - it's a list!")
