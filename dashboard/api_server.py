"""
Simple Flask API server for KB Assist extension
Runs alongside Streamlit dashboard
"""
import sys
import os

# Print startup debug info
print("="*80, flush=True)
print("🚀 KB Assist API Server Starting...", flush=True)
print(f"Python version: {sys.version}", flush=True)
print(f"Working directory: {os.getcwd()}", flush=True)
print(f"Script location: {os.path.dirname(__file__)}", flush=True)
print("="*80, flush=True)

from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from datetime import datetime
import threading
import re

# Add database and utils to path
db_path = os.path.join(os.path.dirname(__file__), 'database')
utils_path = os.path.join(os.path.dirname(__file__), 'utils')
print(f"Adding database path: {db_path}", flush=True)
print(f"Adding utils path: {utils_path}", flush=True)
sys.path.insert(0, db_path)
sys.path.insert(0, utils_path)

try:
    from azure_db import get_connection
    from request_id_generator_sqlite import generate_request_id
    from email_sender import send_submission_confirmation_email, send_ai_auto_rejection_email
    print("✅ Successfully imported database and utils modules", flush=True)
except Exception as e:
    print(f"❌ ERROR importing modules: {e}", flush=True)
    import traceback
    traceback.print_exc()

app = Flask(__name__)
print("✅ Flask app created", flush=True)
# Allow all origins for development (extension runs from chrome-extension:// or extension://)
CORS(app,
     resources={r"/*": {
         "origins": "*",
         "methods": ["GET", "POST", "OPTIONS"],
         "allow_headers": ["Content-Type"],
         "expose_headers": ["Content-Type"],
         "supports_credentials": False
     }},
     send_wildcard=True,
     always_send=True)


def extract_kb_number_from_url(kb_url):
    """Extract KB number from KB article URL"""
    if not kb_url:
        return None
    # Match pattern: tmka-12345 or TMKA-12345
    match = re.search(r'tmka-(\d+)', kb_url, re.IGNORECASE)
    if match:
        return match.group(1)  # Return just the number
    return None


def get_kb_title_from_db(kb_number):
    """Get KB title from database"""
    if not kb_number:
        return None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT title FROM kb_articles WHERE kb_number = %s', (kb_number,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except:
        return None


def parse_perts_for_kb_update(perts_text):
    """
    Parse PERTS to extract:
    - issue_description: What's wrong (PROBLEM_DESCRIPTION + ERROR_MESSAGE + ROOT_CAUSE)
    - proposed_steps: What to add (SOLUTION_THAT_WORKED)
    """
    if not perts_text:
        return perts_text, perts_text

    issue_parts = []
    proposed_solution = []

    lines = perts_text.split('\n')
    current_section = None
    section_content = []

    for line in lines:
        line_upper = line.strip().upper()

        if 'PROBLEM_DESCRIPTION' in line_upper or 'PROBLEM DESCRIPTION' in line_upper:
            if section_content and current_section:
                if current_section == 'solution':
                    proposed_solution.extend(section_content)
                elif current_section in ['problem', 'error', 'root_cause']:
                    issue_parts.extend(section_content)
            current_section = 'problem'
            section_content = []
        elif 'ERROR_MESSAGE' in line_upper or 'ERROR MESSAGE' in line_upper:
            if section_content and current_section in ['problem', 'error', 'root_cause']:
                issue_parts.extend(section_content)
            current_section = 'error'
            section_content = []
        elif 'ROOT_CAUSE' in line_upper or 'ROOT CAUSE' in line_upper:
            if section_content and current_section in ['problem', 'error', 'root_cause']:
                issue_parts.extend(section_content)
            current_section = 'root_cause'
            section_content = []
        elif 'SOLUTION_THAT_WORKED' in line_upper or 'SOLUTION THAT WORKED' in line_upper:
            if section_content and current_section in ['problem', 'error', 'root_cause']:
                issue_parts.extend(section_content)
            current_section = 'solution'
            section_content = []
        elif 'TROUBLESHOOTING' in line_upper:
            if section_content and current_section in ['problem', 'error', 'root_cause']:
                issue_parts.extend(section_content)
            current_section = 'troubleshooting'
            section_content = []
        elif line.strip() and line.strip().lower() not in ['n/a', 'na', 'none']:
            section_content.append(line.strip())

    # Capture last section
    if section_content:
        if current_section == 'solution':
            proposed_solution.extend(section_content)
        elif current_section in ['problem', 'error', 'root_cause']:
            issue_parts.extend(section_content)

    issue_description = '\n'.join(issue_parts).strip() if issue_parts else "Issue not specified"
    proposed_steps = '\n'.join(proposed_solution).strip() if proposed_solution else perts_text

    return issue_description, proposed_steps


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "service": "KB Assist API"})

@app.route('/submit', methods=['POST'])
def submit_report():
    """
    Receive report from browser extension and save to database
    """
    try:
        data = request.json

        # DEBUG: Print incoming data to see if engineer_email is present
        print("\n" + "="*80, flush=True)
        print("INCOMING SUBMISSION DATA:", flush=True)
        print(f"engineer_name: {data.get('engineer_name')}", flush=True)
        print(f"engineer_email: {data.get('engineer_email')}", flush=True)
        print(f"case_number: {data.get('case_number')}", flush=True)
        print(f"ALL DATA: {data}", flush=True)
        print("="*80 + "\n", flush=True)

        # Extract data from request
        case_number = data.get('case_number', 'N/A')
        case_title = data.get('case_title')
        case_status = data.get('case_status')
        case_substatus = data.get('case_substatus')
        product = data.get('product')
        product_version = data.get('product_version')
        os = data.get('os')
        problem_category = data.get('problem_category')
        subcategory = data.get('subcategory')
        kb_article_link = data.get('kb_article_link')
        case_url = data.get('case_url')
        report_type = data.get('report_type')
        new_troubleshooting = data.get('new_troubleshooting', '')
        engineer_notes = data.get('engineer_notes')  # Quick notes from engineer
        engineer_name = data.get('engineer_name')
        engineer_email = data.get('engineer_email')  # ADD THIS
        kb_audience = data.get('kb_audience', 'public')  # Internal or Public KB
        timestamp = data.get('timestamp', datetime.now().isoformat())

        # Validation: Block Premium Service and non-main products
        BLOCKED_PRODUCTS = ['Premium Service', 'Phone', 'My Dashboard', 'MYACCOUNT', 'GENERIC PRODUCT']
        if product in BLOCKED_PRODUCTS:
            return jsonify({
                "success": False,
                "error": f"{product} submissions are not allowed. Please select a core product."
            }), 400

        # Validation: Require kb_article_link for kb_update_request
        if report_type == 'kb_update_request':

            if not kb_article_link or not kb_article_link.strip():
                return jsonify({
                    "success": False,
                    "error": "KB Article URL is required for KB Update Request reports"
                }), 400

            # Validate KB URL format
            if 'helpcenter.trendmicro.com' not in kb_article_link.lower() and 'trendmicro.com' not in kb_article_link.lower():
                return jsonify({
                    "success": False,
                    "error": f"Invalid KB Article URL. Must be a valid Trend Micro Help Center URL. Received: {kb_article_link}"
                }), 400

            if '/article/' not in kb_article_link.lower():
                return jsonify({
                    "success": False,
                    "error": f"Invalid KB Article URL. Must contain /article/ path. Received: {kb_article_link}"
                }), 400

        
        # Determine what_failed based on report_type
        what_failed = None
        if report_type == 'kb_update_request':
            what_failed = new_troubleshooting
        
        # Connect to database
        conn = get_connection()
        cursor = conn.cursor()

        # Generate request ID (simple sequential for now)
        cursor.execute("SELECT COUNT(*) FROM engineer_reports")
        count = cursor.fetchone()[0]
        request_id = f"REQ-{str(count + 1).zfill(6)}"

        # Insert into engineer_reports table
        cursor.execute('''
            INSERT INTO engineer_reports (
                report_date,
                case_number,
                case_title,
                case_status,
                case_substatus,
                product,
                product_version,
                os,
                problem_category,
                subcategory,
                kb_article_link,
                case_url,
                report_type,
                what_failed,
                new_troubleshooting,
                engineer_notes,
                engineer_name,
                engineer_email,
                kb_audience,
                status,
                request_id,
                created_at,
                updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s, %s)
        ''', (
            timestamp,
            case_number,
            case_title,
            case_status,
            case_substatus,
            product,
            product_version,
            os,
            problem_category,
            subcategory,
            kb_article_link,
            case_url,
            report_type,
            what_failed,
            new_troubleshooting,
            engineer_notes,
            engineer_name,
            engineer_email,
            kb_audience,
            request_id,
            timestamp,
            timestamp
        ))
        
        report_id = cursor.lastrowid

        # Commit engineer_reports first
        conn.commit()

        # AI VALIDATION & DECISION LOGIC
        ai_decision = None
        submission_status = "pending"  # Default status

        print(f"[DEBUG] Product: {product}", flush=True)
        print(f"[DEBUG] Report Type: {report_type}", flush=True)

        if product:
            print(f"[DEBUG] Product check PASSED, entering AI validation block", flush=True)
            if report_type == 'kb_update_request':
                print(f"[DEBUG] Report type is kb_update_request, starting AI validation", flush=True)
                # Extract KB info
                kb_number = extract_kb_number_from_url(kb_article_link)
                kb_title = get_kb_title_from_db(kb_number)

                # If KB title not found in database, use placeholder
                if not kb_title:
                    kb_title = f"KB Article {kb_number}"
                    print(f"[DEBUG] KB title not found in database, using placeholder: {kb_title}", flush=True)

                issue_desc, proposed_steps = parse_perts_for_kb_update(new_troubleshooting)
                print(f"[DEBUG] KB Number: {kb_number}, KB Title: {kb_title}", flush=True)
                print(f"[DEBUG] Case URL: {case_url}", flush=True)

                # 🤖 AI VALIDATION: Check if solution already exists
                print(f"\n{'='*80}")
                print(f"🤖 AI VALIDATION for {request_id}")
                print(f"{'='*80}")

                try:
                    from ai_kb_generator import KBGenerator
                    print(f"[DEBUG] KBGenerator imported successfully", flush=True)

                    generator = KBGenerator()
                    print(f"[DEBUG] KBGenerator instance created", flush=True)
                    print(f"[DEBUG] Generator has validate method: {hasattr(generator, 'validate_kb_update_submission')}", flush=True)
                    print(f"[DEBUG] Generator methods: {[m for m in dir(generator) if not m.startswith('_')]}", flush=True)

                    ai_decision = generator.validate_kb_update_submission(
                        kb_number=kb_number,
                        proposed_solution=new_troubleshooting,
                        engineer_notes=engineer_notes
                    )

                    print(f"✅ AI Decision: {ai_decision['decision'].upper()}", flush=True)
                    print(f"📊 Confidence: {ai_decision['confidence']:.0%}", flush=True)
                    print(f"💭 Reasoning: {ai_decision['reasoning']}", flush=True)
                    print(f"{'='*80}\n", flush=True)

                except Exception as e:
                    print(f"⚠️ AI Validation Error: {e}", flush=True)
                    import traceback
                    traceback.print_exc()
                    # Fallback: Auto-approve if AI fails
                    ai_decision = {
                        'is_approved': True,
                        'decision': 'approved',
                        'reasoning': f'AI validation unavailable. Approved for manual review.',
                        'confidence': 0.5
                    }

                # Based on AI decision
                print(f"[DEBUG] AI decision is_approved: {ai_decision['is_approved']}", flush=True)
                if ai_decision['is_approved']:
                    print(f"[DEBUG] APPROVED - Creating kb_update_request entry", flush=True)
                    print(f"[DEBUG] Insert values: kb_number={kb_number}, kb_title={kb_title}, product={product}", flush=True)
                    print(f"[DEBUG] engineer_name={engineer_name}, request_id={request_id}, report_id={report_id}", flush=True)

                    # ✅ APPROVED: Create kb_update_request entry
                    try:
                        cursor.execute('''
                            INSERT INTO kb_update_requests (
                                kb_article_id, kb_article_title,
                                product, issue_description, new_troubleshooting,
                                submitted_by, submitted_date, priority, status,
                                related_report_ids, request_id, case_url, kb_audience
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'medium', 'pending', %s, %s, %s, %s)
                        ''', (kb_number, kb_title, product, issue_desc, new_troubleshooting,
                              engineer_name, timestamp, str(report_id), request_id, case_url, kb_audience))
                        print(f"[DEBUG] INSERT successful!", flush=True)
                    except Exception as insert_error:
                        print(f"[DEBUG] INSERT FAILED: {insert_error}", flush=True)
                        import traceback
                        traceback.print_exc()
                        raise

                    conn.commit()
                    submission_status = "approved"
                    print(f"[DEBUG] kb_update_request created, submission_status set to approved", flush=True)

                    # Send success email
                    try:
                        print(f"[DEBUG] Attempting to send confirmation email to {engineer_email}", flush=True)

                        email_result = send_submission_confirmation_email(
                            request_id=request_id,
                            engineer_email=engineer_email,
                            engineer_name=engineer_name,
                            request_type=report_type,
                            product=product,
                            kb_article_id=kb_number
                        )
                        print(f"📧 Confirmation email sent to {engineer_email}: {email_result}", flush=True)
                    except Exception as e:
                        print(f"⚠️ Email failed: {e}", flush=True)
                        import traceback
                        traceback.print_exc()

                else:
                    print(f"[DEBUG] AUTO-REJECTED - Updating status to auto_rejected", flush=True)
                    # ❌ AUTO-REJECTED: Don't create kb_update_request
                    # Update engineer_reports status to auto_rejected
                    cursor.execute('''
                        UPDATE engineer_reports
                        SET status = 'auto_rejected'
                        WHERE id = %s
                    ''', (report_id,))

                    conn.commit()
                    submission_status = "auto_rejected"
                    print(f"[DEBUG] Status updated to auto_rejected", flush=True)

                    # Send auto-rejection email
                    try:
                        print(f"[DEBUG] Attempting to send rejection email to {engineer_email}", flush=True)

                        email_result = send_ai_auto_rejection_email(
                            request_id=request_id,
                            engineer_email=engineer_email,
                            engineer_name=engineer_name,
                            kb_article_id=kb_number,
                            kb_title=kb_title,
                            reasoning=ai_decision.get('reasoning', 'Solution already exists in KB'),
                            existing_content=ai_decision.get('existing_content'),
                            confidence=ai_decision.get('confidence', 0.9)
                        )
                        print(f"📧 Auto-rejection email sent to {engineer_email}: {email_result}", flush=True)
                    except Exception as e:
                        print(f"⚠️ Email failed: {e}", flush=True)
                        import traceback
                        traceback.print_exc()

            elif report_type == 'no_kb_exists':
                # For new KB requests, just create entry (no AI validation yet)
                cursor.execute('''
                    INSERT INTO new_kb_requests (
                        product, issue_title, issue_description, troubleshooting_steps,
                        submitted_by, submitted_date, priority, status,
                        related_report_ids, request_id, case_url, kb_audience
                    ) VALUES (%s, %s, %s, %s, %s, %s, 'high', 'pending', %s, %s, %s, %s)
                ''', (product, case_title or f"Case {case_number}",
                      new_troubleshooting, new_troubleshooting,
                      engineer_name, timestamp, str(report_id), request_id, case_url, kb_audience))

                conn.commit()
                submission_status = "approved"

                # Send confirmation email
                try:
                    email_result = send_submission_confirmation_email(
                        request_id=request_id,
                        engineer_email=engineer_email,
                        engineer_name=engineer_name,
                        request_type=report_type,
                        product=product
                    )
                    print(f"📧 Confirmation email sent to {engineer_email}: {email_result}", flush=True)
                except Exception as e:
                    print(f"⚠️ Email failed: {e}", flush=True)
                    import traceback
                    traceback.print_exc()

        conn.close()

        # Return response based on AI decision
        print(f"[DEBUG] Building response - submission_status: {submission_status}", flush=True)
        response_data = {
            "success": True,
            "message": "Report submitted successfully",
            "report_id": report_id,
            "request_id": request_id,
            "status": submission_status
        }

        if ai_decision:
            response_data["ai_validation"] = {
                "decision": ai_decision['decision'],
                "reasoning": ai_decision['reasoning'],
                "confidence": ai_decision['confidence']
            }
            print(f"[DEBUG] AI validation included in response", flush=True)
        else:
            print(f"[DEBUG] No AI validation in response", flush=True)

        print(f"[DEBUG] Returning response: {response_data}", flush=True)
        return jsonify(response_data)
        
    except Exception as e:
        print(f"\n{'='*80}", flush=True)
        print(f"❌ SUBMISSION ERROR:", flush=True)
        print(f"Error: {str(e)}", flush=True)
        print(f"{'='*80}\n", flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Log all registered routes
print("="*80, flush=True)
print("✅ All routes registered:", flush=True)
for rule in app.url_map.iter_rules():
    print(f"  {rule.endpoint}: {rule.rule} {list(rule.methods)}", flush=True)
print("="*80, flush=True)

def run_api_server():
    """Run Flask API server"""
    # Get port from environment variable (Render.com) or default to 5000 (localhost)
    port = int(os.getenv('PORT', 5000))
    print(f"🚀 Starting API server on port {port}...", flush=True)
    # Bind to 0.0.0.0 to accept connections from anywhere
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    run_api_server()
