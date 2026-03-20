"""
ULTIMATE SOLUTION - Handles broken LLM responses
Uses multiple fallback strategies to ensure we get real predictions
"""

import csv
import os
import json
from pathlib import Path
import re
import time
import subprocess

import pathway as pw

print("=" * 80)
print("Ultimate Solution - Multiple LLM Strategies")
print("=" * 80)

# -------------------------------------------------
# LOAD NOVELS
# -------------------------------------------------
print("\n[1/6] Loading novels...")

novels = {}
for txt_file in Path("./data").glob("*.txt"):
    try:
        with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
            novels[txt_file.stem.lower().replace("_", " ").replace("-", " ")] = {
                'text': f.read(),
                'file': txt_file.name
            }
        print(f"  ✓ {txt_file.name}")
    except Exception as e:
        print(f"  ✗ {txt_file.name}: {e}")

print(f"✓ Loaded {len(novels)} novels\n")

# -------------------------------------------------
# MULTIPLE LLM STRATEGIES
# -------------------------------------------------
print("[2/6] Setting up LLM strategies...")

def strategy_pathway_llm():
    """Strategy 1: Use Pathway LLM from app.yaml"""
    try:
        with open("app.yaml") as f:
            config = pw.load_yaml(f)
        llm = config.get("$llm")
        if llm:
            # Test it
            test = llm([{"role": "user", "content": "Say OK"}])
            if test and "OK" in str(test).upper():
                return llm, "Pathway LLM"
    except:
        pass
    return None, None

def strategy_direct_ollama():
    """Strategy 2: Direct Ollama API calls"""
    try:
        import requests
        
        def call_ollama(messages):
            url = "http://host.docker.internal:11434/api/chat"
            data = {
                "model": "mistral",
                "messages": messages,
                "stream": False
            }
            response = requests.post(url, json=data, timeout=60)
            if response.status_code == 200:
                return response.json().get('message', {}).get('content', '')
            return None
        
        # Test it
        test = call_ollama([{"role": "user", "content": "Say OK"}])
        if test and "OK" in test.upper():
            return call_ollama, "Direct Ollama"
    except:
        pass
    return None, None

def strategy_subprocess_ollama():
    """Strategy 3: Subprocess call to ollama"""
    try:
        def call_ollama_cli(messages):
            prompt = messages[0]['content']
            result = subprocess.run(
                ['ollama', 'run', 'mistral', prompt],
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.stdout.strip()
        
        # Test it
        test = call_ollama_cli([{"role": "user", "content": "Say OK"}])
        if test and "OK" in test.upper():
            return call_ollama_cli, "Ollama CLI"
    except:
        pass
    return None, None

def strategy_litellm():
    """Strategy 4: Fresh LiteLLMChat instance"""
    try:
        from pathway.xpacks.llm.llms import LiteLLMChat
        
        llm = LiteLLMChat(
            model="ollama/mistral",
            temperature=0.4,
            top_p=1,
            api_base="http://host.docker.internal:11434",
        )
        
        # Test it
        test = llm([{"role": "user", "content": "Say OK"}])
        # Extract text properly
        if isinstance(test, dict):
            text = test.get('content') or test.get('text') or str(test)
        else:
            text = str(test)
        
        if "OK" in text.upper() and "Say OK" not in text:
            return llm, "LiteLLM"
    except:
        pass
    return None, None

# Try strategies in order
print("  Trying strategies...")
llm, strategy_name = strategy_pathway_llm()
if not llm:
    llm, strategy_name = strategy_direct_ollama()
if not llm:
    llm, strategy_name = strategy_subprocess_ollama()
if not llm:
    llm, strategy_name = strategy_litellm()

if llm:
    print(f"  ✓ Using: {strategy_name}")
else:
    print("  ✗ All strategies failed!")
    print("  Please ensure Ollama is running: ollama serve")
    exit(1)

# -------------------------------------------------
# ROBUST LLM CALLER
# -------------------------------------------------

def call_llm_robust(llm_func, messages, max_retries=3):
    """Call LLM with retry logic and response validation"""
    
    for attempt in range(max_retries):
        try:
            response = llm_func(messages)
            
            # Extract text from response
            if isinstance(response, dict):
                text = (response.get('content') or 
                       response.get('text') or 
                       response.get('message', {}).get('content') or
                       str(response))
            elif isinstance(response, str):
                text = response
            else:
                text = str(response)
            
            # Validate: make sure it's not the prompt echoed back
            prompt_snippets = [
                'Format:',
                '[explanation]',
                '[One clear sentence',
                '[detailed explanation]',
                'Answer with:'
            ]
            
            if any(snippet in text for snippet in prompt_snippets):
                print(f"      ⚠ Attempt {attempt+1}: Got prompt back, retrying...")
                time.sleep(1)
                continue
            
            # Validate: must have some content
            if len(text.strip()) < 10:
                print(f"      ⚠ Attempt {attempt+1}: Empty response, retrying...")
                time.sleep(1)
                continue
            
            return text
            
        except Exception as e:
            print(f"      ⚠ Attempt {attempt+1} failed: {e}")
            time.sleep(2)
    
    return None

# -------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------

def match_novel(book_name, novels_dict):
    book_lower = book_name.lower()
    for key in novels_dict.keys():
        if any(w in key for w in book_lower.split() if len(w) > 3):
            return key
    return list(novels_dict.keys())[0]

def get_evidence(char_name, backstory, novel_text):
    keywords = set(re.findall(r'\b[a-z]{4,}\b', backstory.lower())[:15])
    if char_name:
        keywords.add(char_name.lower())
    
    paras = [(sum(1 for kw in keywords if kw in p.lower()), p[:700]) 
             for p in novel_text.split('\n\n') if len(p) > 50]
    paras.sort(reverse=True)
    
    evidence = '\n\n'.join(p for _, p in paras[:5])
    return evidence[:3500] if evidence else novel_text[:3500]

def classify(backstory, char_name, book_name, novel_text, llm_func):
    """Classify with ultra-simple prompt"""
    
    evidence = get_evidence(char_name, backstory, novel_text)
    
    # Super simple prompt that's hard to mess up
    prompt = f"""Novel: {book_name}
Character: {char_name or 'Unknown'}

BACKSTORY: {backstory}

NOVEL EVIDENCE: {evidence}

Is this backstory consistent (YES) or contradictory (NO) with the novel?

Answer ONLY with:
YES - reason
or
NO - reason"""

    messages = [{"role": "user", "content": prompt}]
    response = call_llm_robust(llm_func, messages)
    
    if not response:
        return 0, "LLM failed to respond"
    
    # Parse
    response_lower = response.lower()
    
    # Simple YES/NO detection
    if response.upper().startswith('YES'):
        label = 1
        reason = response.split('-', 1)[-1].strip() if '-' in response else response
    elif response.upper().startswith('NO'):
        label = 0
        reason = response.split('-', 1)[-1].strip() if '-' in response else response
    else:
        # Fallback: sentiment analysis
        negative_terms = ['contradict', 'inconsistent', 'impossible', 'false', 'wrong']
        positive_terms = ['consistent', 'possible', 'plausible', 'true', 'correct']
        
        neg_score = sum(1 for term in negative_terms if term in response_lower)
        pos_score = sum(1 for term in positive_terms if term in response_lower)
        
        label = 1 if pos_score > neg_score else 0
        reason = response.strip()
    
    return label, reason[:200]

# -------------------------------------------------
# LOAD TEST CASES
# -------------------------------------------------
print("\n[3/6] Loading test cases...")

with open("test.csv", encoding="utf-8") as f:
    tests = list(csv.DictReader(f))

print(f"✓ Loaded {len(tests)} test cases\n")

# -------------------------------------------------
# PROCESS
# -------------------------------------------------
print("[4/6] Processing test cases...\n")

results = []

for i, row in enumerate(tests, 1):
    test_id = row['id']
    book_name = row['book_name']
    char_name = row.get('char', '')
    content = row['content']
    
    print(f"[{i}/{len(tests)}] ID {test_id}: {book_name[:25]}...")
    
    novel_key = match_novel(book_name, novels)
    novel_text = novels[novel_key]['text']
    
    try:
        label, reason = classify(content, char_name, book_name, novel_text, llm)
        
        results.append({
            "id": test_id,
            "prediction": label,
            "rationale": reason
        })
        
        status = "✓" if label == 1 else "✗"
        print(f"  {status} {label}: {reason[:60]}...")
        
    except Exception as e:
        print(f"  ERROR: {e}")
        results.append({
            "id": test_id,
            "prediction": 0,
            "rationale": f"Error: {e}"
        })
    
    time.sleep(0.5)

# -------------------------------------------------
# SAVE
# -------------------------------------------------
print("\n[5/6] Saving results...")

with open("results.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["id", "prediction", "rationale"])
    writer.writeheader()
    writer.writerows(results)

print("✓ Saved to results.csv\n")

# -------------------------------------------------
# STATISTICS
# -------------------------------------------------
print("[6/6] Statistics")
print("=" * 80)

c1 = sum(1 for r in results if r['prediction'] == 1)
c0 = sum(1 for r in results if r['prediction'] == 0)

print(f"Total:          {len(results)}")
print(f"Consistent:     {c1} ({c1/len(results)*100:.1f}%)")
print(f"Inconsistent:   {c0} ({c0/len(results)*100:.1f}%)")

if c1 == len(results) or c0 == len(results):
    print("\n⚠️  WARNING: All predictions are the same!")
    print("   This usually means the LLM isn't working properly.")
    print("   Try:")
    print("   1. Check Ollama is running: ollama serve")
    print("   2. Try a different model: ollama pull llama3")
    print("   3. Run diagnose_llm.py to debug")
else:
    print("\n✓ Predictions look good (mixed results)")

print("\nSample predictions:")
for r in results[:5]:
    print(f"  {r['id']}: {r['prediction']} - {r['rationale'][:50]}...")

print("\n" + "=" * 80)
print("✓ COMPLETE")
print("=" * 80)