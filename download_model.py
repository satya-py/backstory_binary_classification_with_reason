from sentence_transformers import SentenceTransformer
import os

print("Downloading model all-MiniLM-L6-v2...", flush=True)
model = SentenceTransformer("all-MiniLM-L6-v2", cache_folder="./cache_root/huggingface/hub")
print("Model downloaded successfully.", flush=True)
