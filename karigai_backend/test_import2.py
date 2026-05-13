import app.services.community_knowledge_service as ckservice

print("Module imported successfully")
print("Module contents:", dir(ckservice))
print("\nNon-private attributes:")
for attr in dir(ckservice):
    if not attr.startswith('_'):
        print(f"  - {attr}")
