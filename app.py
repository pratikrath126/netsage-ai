import os
import json
import csv
from flask import Flask, render_template, request, jsonify, send_from_directory
from dotenv import load_dotenv

try:
    import rule_checker
except ImportError:
    class MockRuleChecker:
        def run_all_checks(self, text):
            return [{"rule": "Mock Check", "status": "pass", "severity": "Low", "message": "rule_checker module not found. This is a mock response."}]
    rule_checker = MockRuleChecker()

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'), static_folder=os.path.join(BASE_DIR, 'static'), static_url_path='/static')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'static'), filename)

# In-memory runtime cache fallback for serverless read-only environments
_MEMORY_CACHE = {}

def get_abs_path(relative_path):
    return os.path.join(BASE_DIR, relative_path)

def read_json(filepath, default_val=None):
    if default_val is None:
        default_val = {}
    abs_path = get_abs_path(filepath)
    # Check in-memory cache first
    if filepath in _MEMORY_CACHE:
        return _MEMORY_CACHE[filepath]
    try:
        with open(abs_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            _MEMORY_CACHE[filepath] = data
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return default_val

def write_json(filepath, data):
    _MEMORY_CACHE[filepath] = data
    abs_path = get_abs_path(filepath)
    try:
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except (OSError, IOError):
        # Read-only filesystem in serverless deployment (Vercel)
        pass

def read_cases():
    cases = []
    abs_path = get_abs_path('cases.csv')
    try:
        with open(abs_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'show_outputs' in row:
                    row['show_outputs'] = row['show_outputs'].replace('\\n', '\n')
                cases.append(row)
    except FileNotFoundError:
        pass
    return cases

@app.route('/')
def dashboard():
    cases = read_cases()
    ai_responses = read_json('data/ai_responses.json')
    human_reviews = read_json('data/human_reviews.json')

    total_cases = len(cases)
    total_reviewed = len(human_reviews)
    
    correct = sum(1 for status in human_reviews.values() if status.get('status') == 'accepted')
    ai_accuracy = round((correct / total_reviewed * 100) if total_reviewed > 0 else 0, 1)

    concept_counts = {}
    severity_counts = {'High': 0, 'Medium': 0, 'Low': 0}
    
    for case in cases:
        concept = case.get('concept_tag', 'Unknown')
        concept_counts[concept] = concept_counts.get(concept, 0) + 1
        
        sev = case.get('severity', 'Low')
        if sev in severity_counts:
            severity_counts[sev] += 1
        else:
            severity_counts[sev] = 1

    review_status_counts = {'accepted': 0, 'edited': 0, 'rejected': 0, 'pending': 0}
    for cid in ai_responses.keys():
        if cid in human_reviews:
            status = human_reviews[cid].get('status', 'pending')
            if status in review_status_counts:
                review_status_counts[status] += 1
            else:
                review_status_counts['pending'] += 1
        else:
            review_status_counts['pending'] += 1

    dashboard_data = {
        'concept_counts': concept_counts,
        'severity_counts': severity_counts,
        'review_status_counts': review_status_counts
    }

    return render_template('dashboard.html', 
                           total_cases=total_cases, 
                           total_reviewed=total_reviewed,
                           ai_accuracy=ai_accuracy,
                           cases_corrected=review_status_counts['edited'] + review_status_counts['rejected'],
                           dashboard_data=json.dumps(dashboard_data))

@app.route('/cases')
def cases_page():
    cases = read_cases()
    return render_template('cases.html', cases=cases)

@app.route('/diagnose')
def diagnose_index():
    cases = read_cases()
    return render_template('diagnose.html', cases=cases, selected_case=None)

@app.route('/diagnose/<case_id>')
def diagnose_case(case_id):
    cases = read_cases()
    selected_case = next((c for c in cases if c.get('case_id') == case_id), None)
    
    if not selected_case:
        return "Case not found", 404

    rule_results = []
    if hasattr(rule_checker, 'run_all_checks'):
        rule_results = rule_checker.run_all_checks(selected_case.get('show_outputs', ''))

    ai_responses = read_json('data/ai_responses.json')
    ai_response = ai_responses.get(case_id)

    return render_template('diagnose.html', cases=cases, selected_case=selected_case, rule_results=rule_results, ai_response=ai_response)

@app.route('/api/diagnose/<case_id>', methods=['POST'])
def api_diagnose(case_id):
    cases = read_cases()
    selected_case = next((c for c in cases if c.get('case_id') == case_id), None)
    if not selected_case:
        return jsonify({"error": "Case not found"}), 404

    try:
        with open(get_abs_path('prompts/diagnose_prompt.md'), 'r', encoding='utf-8') as f:
            prompt_template = f.read()
    except FileNotFoundError:
        prompt_template = "Diagnose this symptom: {symptom}\nTopology: {topology_note}\nOutputs:\n{show_outputs}"

    prompt = prompt_template.replace('{{symptom}}', selected_case.get('symptom', ''))
    prompt = prompt.replace('{{topology_note}}', selected_case.get('topology_note', ''))
    prompt = prompt.replace('{{show_outputs}}', selected_case.get('show_outputs', ''))

    load_dotenv(override=True)
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return jsonify({"error": "OPENROUTER_API_KEY is not set in .env file."}), 500

    try:
        from openai import OpenAI
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        completion = client.chat.completions.create(
            model=os.getenv("MODEL", "deepseek/deepseek-v4-flash-0731"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        response_content = completion.choices[0].message.content.strip()
        if "```json" in response_content:
            response_content = response_content.split("```json")[1].split("```")[0].strip()
        elif "```" in response_content:
            response_content = response_content.split("```")[1].split("```")[0].strip()
        ai_result = json.loads(response_content)
        
        # Only save valid response to data/ai_responses.json
        ai_responses = read_json('data/ai_responses.json')
        ai_responses[case_id] = ai_result
        write_json('data/ai_responses.json', ai_responses)
        return jsonify(ai_result)

    except Exception as e:
        return jsonify({"error": str(e), "root_cause": f"Failed to call AI: {e}"}), 500

@app.route('/review')
def review_page():
    cases = read_cases()
    ai_responses = read_json('data/ai_responses.json')
    human_reviews = read_json('data/human_reviews.json')
    
    reviewable_cases = []
    for c in cases:
        cid = c.get('case_id')
        if cid in ai_responses:
            c_copy = dict(c)
            c_copy['ai_response'] = ai_responses[cid]
            c_copy['review'] = human_reviews.get(cid, None)
            reviewable_cases.append(c_copy)
            
    total_ai = len(ai_responses)
    total_reviewed = len(human_reviews)

    return render_template('review.html', cases=reviewable_cases, total_ai=total_ai, total_reviewed=total_reviewed)

@app.route('/api/review/<case_id>', methods=['POST'])
def api_review(case_id):
    data = request.json
    human_reviews = read_json('data/human_reviews.json')
    human_reviews[case_id] = {
        "status": data.get("status"),
        "reviewer_notes": data.get("reviewer_notes", ""),
        "corrected_diagnosis": data.get("corrected_diagnosis", "")
    }
    write_json('data/human_reviews.json', human_reviews)
    return jsonify({"success": True})

@app.route('/responsible-ai')
def responsible_ai_page():
    log_entries = read_json('data/responsible_ai_log.json', [])
    corrected_count = len(log_entries)
    return render_template('responsible_ai.html', log_entries=log_entries, corrected_count=corrected_count)

if __name__ == '__main__':
    app.run(port=5000, debug=True)
