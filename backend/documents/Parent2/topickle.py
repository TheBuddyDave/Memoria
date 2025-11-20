import json, pickle

with open("Parent2\Price_Elasticity_Model_v5.json") as f:
    model_artifact = json.load(f)

with open("Price_Elasticity_Model_v5.pkl", "wb") as f:
    pickle.dump(model_artifact, f)
