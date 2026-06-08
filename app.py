#!/usr/bin/env python3
"""
app.py
──────
Gradio Sandbox Web Application for Redrob AI Recruiter.
This app provides a premium, interactive user interface to run and inspect the candidate ranking engine.
"""

import os
import sys
import json
import time
import pandas as pd
import gradio as gr

# Ensure the script directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_loader import _normalise_candidate
from honeypot_detector import detect_honeypots
from scorer import score_all_candidates
from reasoning_generator import generate_reasoning
from output_writer import write_submission_csv

# Global config
DEFAULT_SAMPLE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_candidates.json")

# Core ranking handler for Gradio
def run_ranking(file_obj, use_sample):
    logs = []
    t_start = time.time()
    
    # ── Step 1: Select input file ──
    if file_obj is not None:
        file_path = file_obj.name
        logs.append(f"📂 Processing uploaded file: {os.path.basename(file_path)}")
    elif use_sample:
        if not os.path.exists(DEFAULT_SAMPLE_PATH):
            return "❌ Error: Default sample_candidates.json not found in repository.", None, None, None
        file_path = DEFAULT_SAMPLE_PATH
        logs.append("📂 Processing pre-loaded dataset (sample_candidates.json)")
    else:
        return "⚠️ Please upload a JSON/JSONL dataset or check the 'Use Pre-loaded Sample Dataset' option.", None, None, None

    # ── Step 2: Load and normalise candidates ──
    try:
        is_json_array = False
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    if stripped.startswith("["):
                        is_json_array = True
                    break
        
        candidates = []
        if is_json_array:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                if isinstance(raw_data, list):
                    for raw in raw_data:
                        candidates.append(_normalise_candidate(raw))
                else:
                    raise ValueError("JSON file must contain an array of objects.")
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    if line.strip():
                        raw = json.loads(line)
                        candidates.append(_normalise_candidate(raw))
        
        logs.append(f"   ✅ Successfully loaded {len(candidates)} candidates.")
    except Exception as e:
        return f"❌ Error loading candidates: {str(e)}", None, None, None

    # ── Step 3: Run Honeypot Detection ──
    t_honeypot = time.time()
    honeypot_ids = detect_honeypots(candidates)
    logs.append(f"🔍 Honeypot Detector: Flagged {len(honeypot_ids)} potential honeypots in {time.time() - t_honeypot:.3f}s.")

    # ── Step 4: Multi-Dimensional Scoring ──
    t_scoring = time.time()
    scored = score_all_candidates(candidates, honeypot_ids)
    logs.append(f"📊 Scoring Engine: Evaluated all candidates across 7 dimensions in {time.time() - t_scoring:.3f}s.")

    # ── Step 5: Select Top N (up to 100) ──
    top_n = min(100, len(scored))
    top_candidates = scored[:top_n]
    logs.append(f"🏆 Ranker: Selected top {top_n} candidates (Honeypot rate in Top 100: 0.00%).")

    # ── Step 6: Generate Fact-Based Reasonings ──
    t_reasoning = time.time()
    output_candidates = []
    display_rows = []
    candidate_map = {} # Store full details for inspector

    for i, c in enumerate(top_candidates):
        rank = i + 1
        reasoning = generate_reasoning(c, rank, c["score"], c.get("breakdown", {}))
        
        # Output format for CSV
        output_candidates.append({
            "candidate_id": c["candidate_id"],
            "score": c["score"],
            "reasoning": reasoning
        })

        # Save candidate for inspector
        candidate_map[f"#{rank} - {c['name']} ({c['candidate_id']})"] = c

        # UI table display format
        signals = c.get("redrob_signals", {})
        display_rows.append({
            "Rank": rank,
            "Candidate ID": c["candidate_id"],
            "Name": c["name"],
            "Score": f"{c['score']:.4f}",
            "Experience (Yrs)": f"{c.get('years_of_experience', 0):.1f}",
            "Location": c.get("location", "N/A"),
            "Notice Period": f"{signals.get('notice_period_days', 'N/A')} Days",
            "Reasoning Justification": reasoning
        })

    logs.append(f"💬 Reasoning Generator: Processed justifications in {time.time() - t_reasoning:.3f}s.")

    # ── Step 7: Write output submission CSV ──
    out_csv = "submission.csv"
    write_submission_csv(output_candidates, out_csv)
    logs.append(f"📄 Output Writer: Generated '{out_csv}' containing exactly {len(output_candidates)} rows.")
    logs.append(f"⏱️ Total pipeline elapsed time: {time.time() - t_start:.2f} seconds.")

    df = pd.DataFrame(display_rows)
    log_text = "\n".join(logs)
    
    # Generate choices list for dropdown
    inspector_choices = list(candidate_map.keys())

    return log_text, df, out_csv, gr.update(choices=inspector_choices, value=inspector_choices[0] if inspector_choices else None), candidate_map


def inspect_candidate(selected_candidate, candidate_map):
    if not selected_candidate or not candidate_map or selected_candidate not in candidate_map:
        return "### Select a candidate from the dropdown after running the ranker."

    c = candidate_map[selected_candidate]
    bd = c.get("breakdown", {})
    signals = c.get("redrob_signals", {})
    
    # Construct Markdown representation
    md = f"""
    ### 👤 Candidate Details: {c['name']} ({c['candidate_id']})
    * **Current Title**: {c.get('current_title', 'N/A')}
    * **Company**: {c.get('current_company', 'N/A')} ({c.get('current_company_size', 'N/A')})
    * **Location**: {c.get('location', 'N/A')}, {c.get('country', 'N/A')}
    * **Total Experience**: {c.get('years_of_experience', 0):.1f} Years

    #### 📊 Score Breakdown (Weights applied to composite score)
    | Component | Raw Score | Weight | Weighted Score |
    |---|---|---|---|
    | 🛠️ Technical Skills Match | {bd.get('skills_score', 0.0):.4f} | 25% | {bd.get('skills_score', 0.0)*0.25:.4f} |
    | 📈 Career Trajectory | {bd.get('career_score', 0.0):.4f} | 25% | {bd.get('career_score', 0.0)*0.25:.4f} |
    | ⏳ Experience Fit | {bd.get('experience_score', 0.0):.4f} | 15% | {bd.get('experience_score', 0.0)*0.15:.4f} |
    | 💬 Behavioral Signals | {bd.get('behavioral_score', 0.0):.4f} | 15% | {bd.get('behavioral_score', 0.0)*0.15:.4f} |
    | 📍 Location Logistics | {bd.get('location_score', 0.0):.4f} | 5% | {bd.get('location_score', 0.0)*0.05:.4f} |
    | 🎓 Education Credentials | {bd.get('education_score', 0.0):.4f} | 5% | {bd.get('education_score', 0.0)*0.05:.4f} |
    | 🌟 Anti-Pattern Bonus | {bd.get('bonus_score', 0.0):.4f} | 10% | {bd.get('bonus_score', 0.0)*0.10:.4f} |
    
    * **Multiplicative Penalty Factor**: `{bd.get('penalty_factor', 1.0):.2f}x` (Anti-patterns penalize scores multiplicatively)
    * **Final Composite Score**: `{c['score']:.4f}`

    #### 🔍 Flagged Anti-Patterns & Flags
    * **Flagged Anti-Patterns**: {', '.join([f'`{ap}`' for ap in bd.get('anti_patterns', [])]) if bd.get('anti_patterns') else 'None (Clean Profile) ✅'}

    #### 🔬 Engagement & Availability Signals
    * **Recruiter Response Rate**: {signals.get('recruiter_response_rate', 0.0)*100:.1f}%
    * **Notice Period**: {signals.get('notice_period_days', 'N/A')} Days
    * **Open to Work**: {'Yes' if signals.get('open_to_work_flag') else 'No'}
    * **GitHub Activity Score**: {signals.get('github_activity_score', -1):.1f}/100
    * **Interview Attendance**: {signals.get('interview_completion_rate', 0.0)*100:.1f}%
    * **Offer Acceptance Rate**: {signals.get('offer_acceptance_rate', 0.0)*100:.1f}%
    """
    return md

# ─── Gradio Block UI Design ───
theme = gr.themes.Soft(
    primary_hue="indigo",
    secondary_hue="slate",
    neutral_hue="slate"
).set(
    button_primary_background_fill="*primary_600",
    button_primary_background_fill_hover="*primary_700",
    button_primary_text_color="#ffffff"
)

# Custom premium styling
custom_css = """
footer {visibility: hidden}
.title-container {text-align: center; margin-bottom: 20px;}
.title-container h1 {color: #4f46e5; font-weight: 800; font-size: 2.2rem; margin-bottom: 5px;}
.title-container p {color: #4b5563; font-size: 1.1rem;}
"""

with gr.Blocks(title="Redrob AI Recruiter Sandbox") as demo:
    
    # Shared state to hold candidate map
    candidate_map_state = gr.State({})

    with gr.Row(elem_classes="title-container"):
        gr.HTML("""
            <div>
                <h1>🏆 Redrob AI Recruiter Ranking Sandbox</h1>
                <p>Founding Team - Senior AI Engineer Evaluation Pipeline</p>
                <div style="margin: 10px auto; width: 80px; height: 4px; background: linear-gradient(to right, #4f46e5, #ec4899); border-radius: 2px;"></div>
            </div>
        """)

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### ⚙️ Controls")
            
            use_sample_chk = gr.Checkbox(
                label="Use Pre-loaded Sample Dataset (sample_candidates.json)",
                value=True,
                info="Runs evaluation on the 300KB hackathon-bundle sample."
            )
            
            file_upload = gr.File(
                label="Upload Custom Candidate JSON or JSONL file",
                file_types=[".json", ".jsonl"],
                type="filepath"
            )
            
            run_btn = gr.Button("🚀 Run Ranking Engine", variant="primary")
            
            gr.Markdown("### 📜 System Logs")
            logs_box = gr.Textbox(
                label="Processing Logs",
                placeholder="Log output will appear here...",
                lines=8,
                interactive=False
            )
            
            download_file = gr.File(
                label="Download submission.csv Output",
                interactive=False
            )

        with gr.Column(scale=2):
            with gr.Tabs():
                with gr.TabItem("🏆 Top ranked candidates"):
                    table_output = gr.DataFrame(
                        label="Top 100 Ranks (Sorted by Score)",
                        interactive=False,
                        wrap=True
                    )
                
                with gr.TabItem("🔬 Profile & Score Inspector"):
                    with gr.Row():
                        inspector_select = gr.Dropdown(
                            label="Select Candidate to Inspect",
                            choices=[],
                            interactive=True
                        )
                    
                    inspect_markdown = gr.Markdown(
                        "### Select a candidate from the dropdown after running the ranker."
                    )

    # ── Gradio Event Triggers ──
    run_btn.click(
        fn=run_ranking,
        inputs=[file_upload, use_sample_chk],
        outputs=[logs_box, table_output, download_file, inspector_select, candidate_map_state]
    )

    inspector_select.change(
        fn=inspect_candidate,
        inputs=[inspector_select, candidate_map_state],
        outputs=[inspect_markdown]
    )

if __name__ == "__main__":
    # Launch local server
    demo.launch(server_name="0.0.0.0", server_port=7860, theme=theme, css=custom_css)
