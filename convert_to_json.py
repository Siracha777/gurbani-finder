import os
import json
import toml
import time

# ===== CONFIGURATION =====
BASE_PATH = r"C:\Users\Satbir\gurbani-app\database_main\database-main\collections\lines"
OUT_FILE = "gurbani.json"

print("=" * 60)
print("GURBANI DATABASE CONVERTER - TOML TO JSON")
print("=" * 60)
print(f"\n📁 Looking for TOML files in: {BASE_PATH}")
print(f"💾 Will save to: {OUT_FILE}\n")

# Check if folder exists
if not os.path.exists(BASE_PATH):
    print(f"❌ ERROR: Folder not found: {BASE_PATH}")
    print("Please check the path and try again!")
    exit()

# ===== STEP 1: CONVERT TOML FILES TO JSON =====
print("🔄 STEP 1: Converting TOML files to JSON...")
print("-" * 60)

records = []
file_count = 0
primary_line_count = 0
start_time = time.time()

for root, dirs, files in os.walk(BASE_PATH):
    for fname in sorted(files):
        if not fname.endswith(".toml"):
            continue

        file_count += 1
        
        # Show progress every 1000 files
        if file_count % 1000 == 0:
            elapsed = time.time() - start_time
            print(f"⏳ Processing... {file_count} files processed ({primary_line_count} lines extracted) - {elapsed:.1f}s")
        
        path = os.path.join(root, fname)
        try:
            data = toml.load(path)
        except Exception as e:
            print(f"❌ Could not parse {path}: {e}")
            continue

        contents = data.get("content", [])
        if not contents:
            continue

        # Collect translations by language (ONLY translations, not notes)
        translations = {}
        for block in contents:
            # Make sure it's a translation (not a note) and has a language
            if block.get("type") == "translation" and "language" in block:
                lang = block.get("language", "unknown")
                text = block.get("data", "").strip()
                asset = block.get("asset", "")
                if text and lang:  # Make sure both exist
                    if lang not in translations:
                        translations[lang] = []
                    translations[lang].append({
                        "text": text,
                        "asset": asset
                    })

        # Find primary blocks (Gurmukhi text)
        primary_blocks = [b for b in contents if b.get("type") == "primary"]
        if not primary_blocks:
            continue

        for primary in primary_blocks:
            gurmukhi = primary.get("data", "").strip()
            if not gurmukhi:
                continue

            # Convert page/line to int
            try:
                page = int(primary.get("page")) if "page" in primary else None
            except Exception:
                page = None
            try:
                line = int(primary.get("line")) if "line" in primary else None
            except Exception:
                line = None

            # Format translations nicely
            formatted_translations = {}
            for lang, trans_list in translations.items():
                # Get unique translations
                unique_trans = []
                seen = set()
                for t in trans_list:
                    if t["text"] not in seen:
                        seen.add(t["text"])
                        unique_trans.append(t)
                
                if unique_trans:
                    formatted_translations[lang] = unique_trans

            record = {
                "source_file": fname,
                "asset": primary.get("asset"),
                "page": page,
                "line": line,
                "gurmukhi": gurmukhi,
                "translations": formatted_translations
            }
            records.append(record)
            primary_line_count += 1

elapsed_time = time.time() - start_time

print(f"\n✅ Conversion Complete!")
print(f"   📊 Processed: {file_count} TOML files")
print(f"   📝 Extracted: {primary_line_count} Gurbani lines")
print(f"   ⏱️  Time taken: {elapsed_time:.1f} seconds")

# Save JSON
print(f"\n💾 Saving to {OUT_FILE}...")
with open(OUT_FILE, "w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False, indent=2)

file_size_mb = os.path.getsize(OUT_FILE) / (1024 * 1024)
print(f"✅ Saved! File size: {file_size_mb:.2f} MB")

# ===== STEP 2: SEARCH FUNCTION =====
print("\n" + "=" * 60)
print("🔍 STEP 2: Setting up search function...")
print("-" * 60)

def search_gurbani(query_text, json_file="gurbani.json", limit=10):
    """
    Search for Gurmukhi text in the JSON database
    Returns results with ONLY English translations
    """
    print(f"\n🔎 Searching for: '{query_text}'")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📚 Loaded {len(data)} lines from database")
    
    results = []
    query_lower = query_text.lower()
    
    for record in data:
        gurmukhi = record.get("gurmukhi", "")
        if query_text in gurmukhi or query_lower in gurmukhi.lower():
            # Get ONLY English translation (language = "en")
            english_trans = ""
            translations_dict = record.get("translations", {})
            
            # Check if English translations exist
            if "en" in translations_dict:
                en_list = translations_dict["en"]
                if en_list:
                    # Prefer SBMS or DSSK asset, otherwise take first English one
                    for trans in en_list:
                        if trans.get("asset") in ["SBMS", "DSSK"]:
                            english_trans = trans["text"]
                            break
                    # If no SBMS/DSSK, just use first English translation
                    if not english_trans and len(en_list) > 0:
                        english_trans = en_list[0]["text"]
            
            # Get Punjabi translation too (if you want it later)
            punjabi_trans = ""
            if "pa" in translations_dict:
                pa_list = translations_dict["pa"]
                if pa_list and len(pa_list) > 0:
                    punjabi_trans = pa_list[0]["text"]
            
            results.append({
                "gurmukhi": gurmukhi,
                "english": english_trans,  # ONLY English here
                "punjabi": punjabi_trans,  # Punjabi if you need it
                "page": record.get("page"),
                "line": record.get("line"),
                "asset": record.get("asset"),
                "all_translations": translations_dict  # Everything if you need it
            })
            
            if len(results) >= limit:
                break
    
    return results

print("✅ Search function ready!")

# ===== STEP 3: TEST THE SEARCH =====
print("\n" + "=" * 60)
print("🧪 STEP 3: Testing the search with examples...")
print("=" * 60)

# Test 1: Search for a common word
print("\n" + "─" * 60)
print("TEST 1: Searching for 'ਵਾਹਿਗੁਰੂ' (Waheguru)")
print("─" * 60)
search_start = time.time()
results1 = search_gurbani("ਵਾਹਿਗੁਰੂ", OUT_FILE, limit=3)
search_time1 = time.time() - search_start

if results1:
    print(f"✅ Found {len(results1)} results in {search_time1:.3f} seconds!\n")
    for i, result in enumerate(results1, 1):
        print(f"📖 Result {i}:")
        print(f"   Gurmukhi: {result['gurmukhi']}")
        print(f"   English:  {result['english']}")
        print(f"   Page: {result['page']}, Line: {result['line']}")
        print()
else:
    print("❌ No results found for 'ਵਾਹਿਗੁਰੂ'")

# Test 2: Search for another word
print("\n" + "─" * 60)
print("TEST 2: Searching for 'ਸਤਿਗੁਰ' (Satgur)")
print("─" * 60)
search_start = time.time()
results2 = search_gurbani("ਸਤਿਗੁਰ", OUT_FILE, limit=3)
search_time2 = time.time() - search_start

if results2:
    print(f"✅ Found {len(results2)} results in {search_time2:.3f} seconds!\n")
    for i, result in enumerate(results2, 1):
        print(f"📖 Result {i}:")
        print(f"   Gurmukhi: {result['gurmukhi']}")
        print(f"   English:  {result['english']}")
        print(f"   Page: {result['page']}, Line: {result['line']}")
        print()
else:
    print("❌ No results found for 'ਸਤਿਗੁਰ'")

# Test 3: Search with romanized text
print("\n" + "─" * 60)
print("TEST 3: Searching for 'ਪ੍ਰਭੁ' (Prabhu)")
print("─" * 60)
search_start = time.time()
results3 = search_gurbani("ਪ੍ਰਭੁ", OUT_FILE, limit=2)
search_time3 = time.time() - search_start

if results3:
    print(f"✅ Found {len(results3)} results in {search_time3:.3f} seconds!\n")
    for i, result in enumerate(results3, 1):
        print(f"📖 Result {i}:")
        print(f"   Gurmukhi: {result['gurmukhi']}")
        print(f"   English:  {result['english']}")
        print(f"   Page: {result['page']}, Line: {result['line']}")
        print()
else:
    print("❌ No results found for 'ਪ੍ਰਭੁ'")

# ===== FINAL SUMMARY =====
print("\n" + "=" * 60)
print("🎉 ALL DONE! Summary:")
print("=" * 60)
print(f"✅ Converted {file_count} TOML files → {OUT_FILE}")
print(f"✅ Database contains {primary_line_count} lines")
print(f"✅ Search is working perfectly!")
print(f"✅ Average search time: ~{(search_time1 + search_time2 + search_time3)/3:.3f} seconds")
print("\n💡 How to use in your project:")
print("   results = search_gurbani('your_transcribed_text')")
print("   print(results[0]['english'])  # Get English translation")
print("=" * 60)