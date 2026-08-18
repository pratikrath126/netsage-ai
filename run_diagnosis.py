import os
import csv
import json
import argparse
from dotenv import load_dotenv
from openai import OpenAI

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='Process only the first case')
    parser.add_argument('--case', type=str, help='Process a single specific case')
    args = parser.parse_args()

    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY not found in environment.")
        return
    model = os.getenv("MODEL", "deepseek/deepseek-v4-flash-0731")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )

    try:
        with open('prompts/diagnose_prompt.md', 'r', encoding='utf-8') as f:
            prompt_template = f.read()
    except FileNotFoundError:
        print("Error: prompts/diagnose_prompt.md not found.")
        return

    cases = []
    try:
        with open('cases.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cases.append(row)
    except FileNotFoundError:
        print("Error: cases.csv not found.")
        return

    if args.test:
        cases = cases[:1]
    elif args.case:
        cases = [c for c in cases if c.get('case_id') == args.case]
        if not cases:
            print(f"Error: Case {args.case} not found.")
            return

    os.makedirs('data', exist_ok=True)
    # Load existing responses so we don't lose previous data
    try:
        with open('data/ai_responses.json', 'r', encoding='utf-8') as f:
            responses_dict = json.load(f)
            if isinstance(responses_dict, list):
                responses_dict = {}
    except (FileNotFoundError, json.JSONDecodeError):
        responses_dict = {}

    matches = 0
    mismatches = []

    print(f"Processing {len(cases)} case(s)...")

    for i, case in enumerate(cases, 1):
        case_id = case.get('case_id', f'Case-{i}')
        print(f"Processing case {i} of {len(cases)} ({case_id})...")

        symptom = case.get('symptom', '')
        topology_note = case.get('topology_note', '')
        show_outputs = case.get('show_outputs', '').replace('\\n', '\n')
        expected_fault = case.get('expected_fault', '')

        prompt_text = prompt_template.replace('{{symptom}}', symptom)
        prompt_text = prompt_text.replace('{{topology_note}}', topology_note)
        prompt_text = prompt_text.replace('{{show_outputs}}', show_outputs)

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt_text}],
                temperature=0.3
            )
            ai_response_text = response.choices[0].message.content
            
            # Simple extraction of JSON
            ai_response_text_clean = ai_response_text
            if "```json" in ai_response_text_clean:
                ai_response_text_clean = ai_response_text_clean.split("```json")[1].split("```")[0].strip()
            elif "```" in ai_response_text_clean:
                ai_response_text_clean = ai_response_text_clean.split("```")[1].split("```")[0].strip()
                
            parsed_json = json.loads(ai_response_text_clean)
            root_cause = parsed_json.get('root_cause', '')
            
            # Simple substring match (case insensitive)
            match = expected_fault.lower() in root_cause.lower() if expected_fault else False
            if match:
                matches += 1
            else:
                mismatches.append((case_id, expected_fault, root_cause))

            # Save as dict keyed by case_id (matches app.py format)
            responses_dict[case_id] = parsed_json
            
        except Exception as e:
            print(f"Error processing {case_id}: {e}")
            responses_dict[case_id] = {
                "root_cause": f"Error: {str(e)}",
                "confidence": "low",
                "evidence": "",
                "next_command": "",
                "fix_steps": [],
                "osi_layer": "Unknown"
            }

    with open('data/ai_responses.json', 'w', encoding='utf-8') as f:
        json.dump(responses_dict, f, indent=2)

    total_cases = len(cases)
    print(f"\nSummary: {matches}/{total_cases} cases matched.")
    if mismatches:
        print("Mismatches:")
        for case_id, expected, got in mismatches:
            print(f"  - {case_id}: Expected '{expected}', got '{got}'")
if __name__ == '__main__':
    main()
