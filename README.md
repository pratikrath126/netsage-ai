# 🌐 NetSage AI — Network Troubleshooting Assistant with Human Review

[![Live Demo](https://img.shields.io/badge/Demo-Live_on_Vercel-success?style=for-the-badge&logo=vercel)](https://netsage-ai-tawny.vercel.app/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Framework-Flask-black?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

> **NetSage AI** is an AI-powered diagnostic and troubleshooting helper designed for Cisco-style lab networks and Packet Tracer scenarios. It analyzes symptoms, network topology notes, and CLI `show` command outputs to pinpoint root causes, identify the affected OSI layer, suggest the next diagnostic commands, and generate evidence-backed fixes—with mandatory human review and verification.

---

## 🚀 Live Demo

🔗 **Production URL:** [https://netsage-ai-tawny.vercel.app/](https://netsage-ai-tawny.vercel.app/)

---

## 📌 Problem Statement

Junior network engineers frequently memorize individual commands but struggle to connect symptoms to the underlying root cause. When a host receives an IP address but cannot reach a server, the root issue could span VLANs, routing, DHCP, DNS, ACLs, or NAT. 

**NetSage AI bridges this gap** by:
1. Applying **deterministic rule checks** to catch fundamental misconfigurations (IP conflicts, subnet mask mismatches, down interfaces).
2. Leveraging **structured LLM prompts** to analyze multi-device CLI outputs and recommend actionable fixes.
3. Requiring **human-in-the-loop oversight** where network engineers review, edit, or reject AI diagnoses, logging edge cases for responsible AI governance.

---

## 🌟 Key Features

* **🗂️ 40 Realistic Cisco Lab Scenarios:** Covering 8 network domains:
  * **VLANs & Trunks:** Access/trunk misconfigs, missing VLANs, native VLAN mismatches, STP loops.
  * **Routing & Gateways:** Missing static/default routes, OSPF Area mismatches, passive interfaces.
  * **DHCP:** Scope network mismatches, missing default-router, excluded address conflicts, DHCP snooping.
  * **DNS:** Domain-lookup disabled, local host entries, external reachability.
  * **ACLs:** Implicit deny blocks, wrong direction (in/out), named ACL typos, permit/deny ordering.
  * **NAT / PAT:** Missing `ip nat inside/outside`, pool exhaustion, port forwarding translations.
  * **Wireless LAN:** SSID administrative shutdown, WPA2-PSK key mismatches, BVI DHCP relay.
  * **Interface & Layer 1:** Duplex/speed collisions, administratively down states, MTU DF-bit drops.
* **🔍 Deterministic Rule Checker (`rule_checker.py`):** Standalone Python module executing regex-based checks for rapid pre-diagnostic validation without consuming API tokens.
* **🤖 Structured AI Prompts with Strict JSON Schemas:** Prompts enforce structured outputs with `root_cause`, `confidence`, `evidence`, `next_command`, `fix_steps`, and `osi_layer`.
* **⚡ Live Real-Time Diagnosis UI:** Interactive diagnosis with animated analysis states, pulse glow highlights, and human-readable formatted cards (no raw JSON).
* **✍️ Human Review System:** Accept, edit (with notes and corrected diagnosis), or reject AI evaluations.
* **📊 Analytics Dashboard:** Real-time visual metrics powered by Chart.js:
  * *Cases by Concept* (Bar chart with natural domain distribution)
  * *Severity Breakdown* (Pie chart: High, Medium, Low)
  * *Review Status* (Doughnut chart: Accepted, Edited, Rejected, Pending)
* **💡 Responsible AI Log:** Documented record of edge cases where the AI needed human correction, detailing the root cause, failure rationale, and engineering takeaways.

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| **Backend** | Python 3.x, Flask | Web routing, serverless WSGI API endpoints |
| **Frontend** | Vanilla HTML5, CSS3, JavaScript | Lightweight, zero-dependency responsive interface |
| **Charts** | Chart.js (CDN) | Interactive dashboard analytics & distributions |
| **AI Integration** | OpenRouter API (`openai` SDK) | DeepSeek V4 Flash / Gemini Flash structured inference |
| **Data Storage** | Flat-file CSV & JSON | Zero-database footprint (`cases.csv`, `data/*.json`) |
| **Deployment** | Vercel Serverless | Python WSGI serverless function deployment |

---

## 📂 Project Structure

```
netsage-ai/
├── app.py                     # Main Flask web application & API routes
├── cases.csv                  # 40 Cisco network troubleshooting lab scenarios
├── rule_checker.py            # Standalone deterministic validation script
├── run_diagnosis.py           # Batch AI diagnosis runner
├── requirements.txt           # Python dependencies
├── vercel.json                # Vercel serverless deployment routing
├── DEPLOYMENT_GUIDE.md        # Detailed deployment walkthrough
│
├── prompts/
│   ├── diagnose_prompt.md     # Primary structured diagnosis prompt with examples
│   └── followup_prompt.md     # Follow-up investigation prompt
│
├── data/
│   ├── ai_responses.json      # Stored AI diagnoses across all cases
│   ├── human_reviews.json     # Human-in-the-loop review decisions & notes
│   └── responsible_ai_log.json# Documented AI corrections & lessons learned
│
├── templates/
│   ├── base.html              # Core navigation layout & CDN imports
│   ├── dashboard.html         # Analytics dashboard & Chart.js charts
│   ├── cases.html             # Filterable case browser with expandable details
│   ├── diagnose.html          # Interactive live AI diagnosis interface
│   ├── review.html            # Human review & editing interface
│   └── responsible_ai.html    # Responsible AI transparency log
│
└── static/
    ├── style.css              # Custom styling, animations & responsive grid
    └── script.js              # Client-side chart rendering & real-time AJAX logic
```

---

## 💻 Local Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/pratikrath126/netsage-ai.git
cd netsage-ai
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
Create a `.env` file in the root directory:
```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
MODEL=deepseek/deepseek-v4-flash-0731
```

### 4. Run the application
```bash
python app.py
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser.

---

## 🧪 CLI Scripts

### Run Deterministic Rule Checker
```bash
python rule_checker.py
```

### Run Batch AI Diagnosis on all cases
```bash
python run_diagnosis.py
```
*Test a single case:*
```bash
python run_diagnosis.py --case CASE-003
```

---

## ☁️ Deploying to Vercel

1. Push code to your GitHub repository.
2. Import the repository in [Vercel](https://vercel.com/new).
3. Set the Environment Variables:
   * `OPENROUTER_API_KEY`: `your_key`
   * `MODEL`: `deepseek/deepseek-v4-flash-0731`
4. Click **Deploy**.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
