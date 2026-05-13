import traceback

try:
    from app.services.community_knowledge_service import CommunityKnowledgeService
    print("Success! Class imported")
    print(f"Class: {CommunityKnowledgeService}")
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
