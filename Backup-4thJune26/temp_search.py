import json
import sys
sys.stdout.reconfigure(encoding='utf-8')
for line in open(r'C:\Users\bipla\.gemini\antigravity\brain\b0dd8235-b3d8-4f27-bc7e-af95c79fff92\.system_generated\logs\transcript.jsonl', encoding='utf-8'):
    try:
        data = json.loads(line)
        content = data.get('content', '')
        if '6 min' in content or '6-min' in content or '6 mins' in content:
            print(f"--- STEP {data.get('step_index')} [{data.get('source')} - {data.get('type')}] ---")
            print(content)
    except Exception:
        pass
