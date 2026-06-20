import json
import random
import re
from pathlib import Path

def get_random_article(file_path: Path):
    file_size = file_path.stat().st_size
    
    with open(file_path, 'rb') as f:
        # Seek to a random byte in the file
        random_offset = random.randint(0, max(0, file_size - 1))
        f.seek(random_offset)
        
        # If we didn't land exactly at the start, discard the partial line
        if random_offset != 0:
            f.readline()
            
        # Read the next full line
        line = f.readline()
        
        # If we hit EOF (meaning our random seek was on the very last line), wrap around to the top
        if not line:
            f.seek(0)
            line = f.readline()
            
        return json.loads(line.decode('utf-8'))

def main():
    base_dir = Path(__file__).resolve().parent.parent.parent
    json_path = base_dir / 'data' / 'eswiki-20260301-pages-articles.json'
    dict_path = base_dir / 'data' / 'dictionaries' / 'dic_es.txt'
    
    if not json_path.exists():
        print(f"Error: JSON file not found at {json_path}")
        return
    
    if not dict_path.exists():
        print(f"Error: Dictionary file not found at {dict_path}")
        return
        
    print("Loading dictionary...")
    with open(dict_path, 'r', encoding='utf-8') as f:
        valid_words = set(word.strip().lower() for word in f if word.strip())
        
    print(f"Loaded {len(valid_words)} unique words from dictionary.")
    
    from collections import Counter
    results = []
    
    print("Sampling 50 articles...")
    for i in range(50):
        article = get_random_article(json_path)
        
        text = article.get('clean_text', '')
        if not text:
            text = article.get('text', '')
            
        rev_id = article.get('revision_id', f'unknown_{i}')
        
        words = re.findall(r'[a-záéíóúüñ]+', text.lower())
        if not words:
            # If no words, assign 0 percentage
            results.append({
                'revision_id': rev_id,
                'percentage': 0.0,
                'unknown': []
            })
            continue
            
        found_words = 0
        not_found = []
        
        for word in words:
            if word in valid_words:
                found_words += 1
            else:
                not_found.append(word)
                
        percentage = (found_words / len(words)) * 100
        
        common_unknown = []
        if not_found:
            most_common = Counter(not_found).most_common(10)
            common_unknown = [f"{w}({c})" for w, c in most_common]
            
        results.append({
            'revision_id': rev_id,
            'percentage': percentage,
            'unknown': common_unknown
        })
        
        if (i + 1) % 10 == 0:
            print(f"Sampled {i+1}/50 articles...")

    results.sort(key=lambda x: x['percentage'])
    
    output_path = Path(__file__).resolve().parent / 'output.txt'
    print(f"Writing results to {output_path}...")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for res in results:
            unknown_str = ", ".join(res['unknown'])
            f.write(f"{res['revision_id']} - {res['percentage']:.2f}% - [{unknown_str}]\n")
            
    print("Done!")

if __name__ == "__main__":
    main()
