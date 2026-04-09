"""
KB Assist Cloud API Server - Azure SQL Version
Receives reports from browser extension and saves to Azure SQL Database
Multi-user support with centralized database
"""
from flask import Flask, request, jsonify, render_template_string, redirect, url_for
from flask_cors import CORS
from datetime import datetime
import sys
import os

# Add database directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'database'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))

from azure_db import get_connection_context
from request_id_generator import generate_request_id

# Optional: Token generator for revision/verification portals
try:
    from token_generator import validate_token, mark_token_used
    TOKENS_ENABLED = True
except ImportError:
    TOKENS_ENABLED = False
    print("⚠️  Token generator not available - revision/verification portals disabled")

app = Flask(__name__)

# Allow all origins for extension access
CORS(app, resources={r"/*": {
    "origins": "*",
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type"],
    "expose_headers": ["Content-Type"],
    "supports_credentials": False
}})

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        # Test database connection
        with get_connection_context() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM engineer_reports')
            count = cursor.fetchone()[0]

        return jsonify({
            "service": "KB Assist Cloud API (Azure SQL)",
            "status": "ok",
            "database": "connected",
            "total_reports": count,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "service": "KB Assist Cloud API (Azure SQL)",
            "status": "error",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/submit', methods=['POST'])
def submit_report():
    """Submit a new report"""
    try:
        data_received = request.json

        # Extract fields
        case_number = data_received.get('case_number', 'N/A')
        case_title = data_received.get('case_title')
        case_status = data_received.get('case_status')
        case_substatus = data_received.get('case_substatus')
        product = data_received.get('product', 'Unknown')
        product_version = data_received.get('product_version')
        os_name = data_received.get('os')
        problem_category = data_received.get('problem_category')
        subcategory = data_received.get('subcategory')
        kb_article_link = data_received.get('kb_article_link')
        kb_article_id = data_received.get('kb_article_id')
        kb_article_title = data_received.get('kb_article_title')
        report_type = data_received.get('report_type', 'unknown')
        what_failed = data_received.get('what_failed', '')
        new_troubleshooting = data_received.get('new_troubleshooting', '')
        engineer_name = data_received.get('engineer_name', 'Unknown')
        engineer_email = data_received.get('engineer_email', '')
        timestamp = data_received.get('timestamp', datetime.now().isoformat())

        # Insert into Azure SQL
        with get_connection_context() as conn:
            cursor = conn.cursor()

            # Generate unique request ID (pass connection for sequential numbering)
            request_id = generate_request_id(conn)

            # Insert engineer report
            cursor.execute('''
                INSERT INTO engineer_reports (
                    report_date, case_number, kb_article_id, kb_article_title,
                    product, report_type, what_failed, new_troubleshooting,
                    engineer_name, engineer_email, status, request_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s)
            ''', (
                timestamp,
                case_number,
                kb_article_id,
                kb_article_title or case_title,
                product,
                report_type,
                what_failed,
                new_troubleshooting,
                engineer_name,
                engineer_email,
                request_id
            ))

            # Get the inserted report ID
            cursor.execute('SELECT @@IDENTITY')
            report_id = cursor.fetchone()[0]

            # Create KB update request if needed
            if report_type in ['kb_outdated', 'kb_missing_steps'] and kb_article_id:
                cursor.execute('''
                    INSERT INTO kb_update_requests (
                        kb_article_id, kb_article_title, product,
                        issue_description, new_troubleshooting,
                        submitted_by, submitted_date, priority, status,
                        related_report_ids, request_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'medium', 'pending', %s, %s)
                ''', (
                    kb_article_id,
                    kb_article_title or case_title,
                    product,
                    what_failed or f"{report_type}: {case_title or case_number}",
                    new_troubleshooting,
                    engineer_name,
                    timestamp,
                    str(report_id),
                    request_id
                ))

            # Create new KB request if needed
            elif report_type == 'no_kb_exists':
                cursor.execute('''
                    INSERT INTO new_kb_requests (
                        issue_title, product, issue_description,
                        troubleshooting_steps, submitted_by,
                        submitted_date, priority, status,
                        related_report_ids, request_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, 'high', 'pending', %s, %s)
                ''', (
                    case_title or f"Case {case_number}",
                    product,
                    what_failed or new_troubleshooting,
                    new_troubleshooting,
                    engineer_name,
                    timestamp,
                    str(report_id),
                    request_id
                ))

            # Update KB statistics
            if kb_article_id and report_type != 'no_kb_exists':
                # Check if KB stats exist
                cursor.execute(
                    'SELECT kb_article_id FROM kb_statistics WHERE kb_article_id = %s',
                    (kb_article_id,)
                )
                exists = cursor.fetchone()

                if exists:
                    # Update existing stats
                    cursor.execute(f'''
                        UPDATE kb_statistics
                        SET total_reports = total_reports + 1,
                            {f"success_count = success_count + 1," if report_type == 'kb_worked' else ''}
                            {f"failed_count = failed_count + 1," if report_type == 'kb_failed' else ''}
                            {f"outdated_count = outdated_count + 1," if report_type == 'kb_outdated' else ''}
                            last_reported = %s,
                            last_updated = GETDATE()
                        WHERE kb_article_id = %s
                    ''', (timestamp, kb_article_id))
                else:
                    # Create new stats entry
                    cursor.execute('''
                        INSERT INTO kb_statistics (
                            kb_article_id, kb_article_title, product,
                            total_reports, success_count, failed_count,
                            outdated_count, last_reported
                        ) VALUES (%s, %s, %s, 1, %s, %s, %s, %s)
                    ''', (
                        kb_article_id,
                        kb_article_title,
                        product,
                        1 if report_type == 'kb_worked' else 0,
                        1 if report_type == 'kb_failed' else 0,
                        1 if report_type == 'kb_outdated' else 0,
                        timestamp
                    ))

        return jsonify({
            "success": True,
            "message": "Report submitted successfully to Azure SQL",
            "report_id": int(report_id),
            "request_id": request_id
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/reports', methods=['GET'])
def get_reports():
    """Get all reports (for dashboard)"""
    try:
        with get_connection_context() as conn:
            cursor = conn.cursor()

            # Get all engineer reports
            cursor.execute('SELECT * FROM engineer_reports ORDER BY report_date DESC')
            reports = []
            for row in cursor.fetchall():
                reports.append({
                    'id': row[0],
                    'report_date': str(row[1]),
                    'case_number': row[2],
                    'kb_article_id': row[3],
                    'kb_article_title': row[4],
                    'product': row[5],
                    'report_type': row[6],
                    'what_failed': row[7],
                    'engineer_name': row[10],
                    'engineer_email': row[11],
                    'status': row[14]
                })

            # Get KB update requests
            cursor.execute('SELECT * FROM kb_update_requests ORDER BY submitted_date DESC')
            kb_updates = []
            for row in cursor.fetchall():
                kb_updates.append({
                    'id': row[0],
                    'kb_article_id': row[1],
                    'product': row[3],
                    'issue_description': row[4],
                    'new_troubleshooting': row[5],
                    'submitted_by': row[6],
                    'status': row[8],
                    'priority': row[9]
                })

            # Get new KB requests
            cursor.execute('SELECT * FROM new_kb_requests ORDER BY submitted_date DESC')
            new_kbs = []
            for row in cursor.fetchall():
                new_kbs.append({
                    'id': row[0],
                    'issue_title': row[1],
                    'product': row[2],
                    'troubleshooting_steps': row[4],
                    'submitted_by': row[5],
                    'status': row[7],
                    'priority': row[8]
                })

        return jsonify({
            "success": True,
            "reports": reports,
            "kb_update_requests": kb_updates,
            "new_kb_requests": new_kbs,
            "total_reports": len(reports)
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/revise/<token>', methods=['GET', 'POST'])
def revise_request(token):
    """Engineer revision portal - revise a rejected request"""
    if not TOKENS_ENABLED:
        return jsonify({"error": "Revision portal not available"}), 503

    try:
        with get_connection_context() as conn:
            # Validate token
            token_data = validate_token(conn, token, 'revise')

            if not token_data:
                return render_template_string(ERROR_PAGE_TEMPLATE,
                    error_title="Invalid Link",
                    error_message="This revision link is invalid or has been removed."
                ), 404

            if not token_data.get('valid'):
                return render_template_string(ERROR_PAGE_TEMPLATE,
                    error_title=("Expired Link" if 'expired' in token_data.get('error', '') else "Link Already Used"),
                    error_message=token_data.get('error')
                ), 400

            request_id = token_data['request_id']
            request_type = token_data['request_type']
            engineer_email = token_data['engineer_email']

            # GET: Show revision form
            if request.method == 'GET':
                # Fetch request data
                cursor = conn.cursor()

                if request_type == 'kb_update':
                    cursor.execute('''
                        SELECT kb_article_id, kb_article_title, product,
                               issue_description, new_troubleshooting,
                               submitted_by, feedback_text
                        FROM kb_update_requests
                        WHERE request_id = %s
                    ''', (request_id,))
                else:  # new_kb
                    cursor.execute('''
                        SELECT issue_title, product, issue_description,
                               troubleshooting_steps, submitted_by, feedback_text
                        FROM new_kb_requests
                        WHERE request_id = %s
                    ''', (request_id,))

                row = cursor.fetchone()
                if not row:
                    return render_template_string(ERROR_PAGE_TEMPLATE,
                        error_title="Request Not Found",
                        error_message=f"Request {request_id} not found in database."
                    ), 404

                # Build form data
                if request_type == 'kb_update':
                    form_data = {
                        'request_id': request_id,
                        'kb_article_id': row[0],
                        'kb_article_title': row[1],
                        'product': row[2],
                        'issue_description': row[3],
                        'new_troubleshooting': row[4],
                        'submitted_by': row[5],
                        'feedback_text': row[6],
                        'request_type': 'kb_update'
                    }
                else:
                    form_data = {
                        'request_id': request_id,
                        'issue_title': row[0],
                        'product': row[1],
                        'issue_description': row[2],
                        'troubleshooting_steps': row[3],
                        'submitted_by': row[4],
                        'feedback_text': row[5],
                        'request_type': 'new_kb'
                    }

                return render_template_string(REVISION_FORM_TEMPLATE, **form_data)

            # POST: Submit revised request
            else:
                data = request.form
                cursor = conn.cursor()

                if request_type == 'kb_update':
                    # Update KB update request
                    cursor.execute('''
                        UPDATE kb_update_requests
                        SET issue_description = %s,
                            new_troubleshooting = %s,
                            status = 'pending',
                            submitted_date = GETDATE()
                        WHERE request_id = %s
                    ''', (
                        data.get('issue_description'),
                        data.get('new_troubleshooting'),
                        request_id
                    ))
                else:  # new_kb
                    # Update new KB request
                    cursor.execute('''
                        UPDATE new_kb_requests
                        SET issue_title = %s,
                            issue_description = %s,
                            troubleshooting_steps = %s,
                            status = 'pending',
                            submitted_date = GETDATE()
                        WHERE request_id = %s
                    ''', (
                        data.get('issue_title'),
                        data.get('issue_description'),
                        data.get('troubleshooting_steps'),
                        request_id
                    ))

                # Mark token as used
                mark_token_used(conn, token)
                conn.commit()

                return render_template_string(SUCCESS_PAGE_TEMPLATE,
                    success_title="Request Updated Successfully!",
                    success_message=f"Your request {request_id} has been updated and resubmitted for review."
                )

    except Exception as e:
        return render_template_string(ERROR_PAGE_TEMPLATE,
            error_title="Error",
            error_message=str(e)
        ), 500

@app.route('/verify/<token>', methods=['GET', 'POST'])
def verify_kb(token):
    """Engineer verification portal - verify approved KB"""
    if not TOKENS_ENABLED:
        return jsonify({"error": "Verification portal not available"}), 503

    try:
        with get_connection_context() as conn:
            # Validate token
            token_data = validate_token(conn, token, 'verify')

            if not token_data:
                return render_template_string(ERROR_PAGE_TEMPLATE,
                    error_title="Invalid Link",
                    error_message="This verification link is invalid or has been removed."
                ), 404

            if not token_data.get('valid'):
                return render_template_string(ERROR_PAGE_TEMPLATE,
                    error_title=("Expired Link" if 'expired' in token_data.get('error', '') else "Link Already Used"),
                    error_message=token_data.get('error')
                ), 400

            request_id = token_data['request_id']
            request_type = token_data['request_type']
            kb_link = token_data.get('kb_link', '')

            # GET: Show verification form
            if request.method == 'GET':
                return render_template_string(VERIFICATION_FORM_TEMPLATE,
                    request_id=request_id,
                    kb_link=kb_link,
                    request_type=request_type
                )

            # POST: Submit verification
            else:
                data = request.form
                verification_status = data.get('verification_status')  # 'correct' or 'incorrect'
                comments = data.get('comments', '')

                cursor = conn.cursor()

                if request_type == 'kb_update':
                    cursor.execute('''
                        UPDATE kb_update_requests
                        SET status = %s,
                            verification_status = %s,
                            verification_comments = %s,
                            verified_date = GETDATE()
                        WHERE request_id = %s
                    ''', (
                        'verified' if verification_status == 'correct' else 'needs_revision',
                        verification_status,
                        comments,
                        request_id
                    ))
                else:  # new_kb
                    cursor.execute('''
                        UPDATE new_kb_requests
                        SET status = %s,
                            verification_status = %s,
                            verification_comments = %s,
                            verified_date = GETDATE()
                        WHERE request_id = %s
                    ''', (
                        'verified' if verification_status == 'correct' else 'needs_revision',
                        verification_status,
                        comments,
                        request_id
                    ))

                # Mark token as used
                mark_token_used(conn, token)
                conn.commit()

                if verification_status == 'correct':
                    return render_template_string(SUCCESS_PAGE_TEMPLATE,
                        success_title="KB Verified Successfully!",
                        success_message=f"Thank you for verifying the KB article for request {request_id}."
                    )
                else:
                    return render_template_string(SUCCESS_PAGE_TEMPLATE,
                        success_title="Feedback Submitted",
                        success_message=f"Your feedback for request {request_id} has been submitted. The KB team will review your comments."
                    )

    except Exception as e:
        return render_template_string(ERROR_PAGE_TEMPLATE,
            error_title="Error",
            error_message=str(e)
        ), 500

# HTML Templates for Portal Pages
ERROR_PAGE_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>{{ error_title }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            text-align: center;
        }
        .error-box {
            background-color: #fee;
            border: 2px solid #d71921;
            border-radius: 8px;
            padding: 30px;
        }
        h1 { color: #d71921; }
        p { color: #333; font-size: 16px; }
    </style>
</head>
<body>
    <div class="error-box">
        <h1>❌ {{ error_title }}</h1>
        <p>{{ error_message }}</p>
    </div>
</body>
</html>
'''

SUCCESS_PAGE_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>{{ success_title }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            text-align: center;
        }
        .success-box {
            background-color: #efe;
            border: 2px solid #4CAF50;
            border-radius: 8px;
            padding: 30px;
        }
        h1 { color: #4CAF50; }
        p { color: #333; font-size: 16px; }
    </style>
</head>
<body>
    <div class="success-box">
        <h1>✅ {{ success_title }}</h1>
        <p>{{ success_message }}</p>
    </div>
</body>
</html>
'''

REVISION_FORM_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Revise Request {{ request_id }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 30px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #d71921;
            border-bottom: 2px solid #d71921;
            padding-bottom: 10px;
        }
        .info-box {
            background-color: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin: 20px 0;
        }
        .feedback-box {
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
        }
        label {
            display: block;
            margin-top: 15px;
            font-weight: bold;
            color: #333;
        }
        input[type="text"], textarea {
            width: 100%;
            padding: 10px;
            margin-top: 5px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-family: Arial, sans-serif;
            box-sizing: border-box;
        }
        textarea {
            min-height: 150px;
            resize: vertical;
        }
        button {
            background-color: #d71921;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            margin-top: 20px;
        }
        button:hover {
            background-color: #b51519;
        }
        .readonly {
            background-color: #f5f5f5;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>✏️ Revise Your KB Request</h1>

        <div class="info-box">
            <strong>Request ID:</strong> {{ request_id }}<br>
            <strong>Submitted by:</strong> {{ submitted_by }}
        </div>

        {% if feedback_text %}
        <div class="feedback-box">
            <strong>📝 Manager's Feedback:</strong><br>
            {{ feedback_text }}
        </div>
        {% endif %}

        <form method="POST">
            {% if request_type == 'kb_update' %}
                <label>KB Article ID:</label>
                <input type="text" value="{{ kb_article_id }}" class="readonly" readonly>

                <label>KB Article Title:</label>
                <input type="text" value="{{ kb_article_title }}" class="readonly" readonly>

                <label>Product:</label>
                <input type="text" value="{{ product }}" class="readonly" readonly>

                <label>What's Wrong / Missing: *</label>
                <textarea name="issue_description" required>{{ issue_description }}</textarea>

                <label>Proposed New Steps to Add: *</label>
                <textarea name="new_troubleshooting" required>{{ new_troubleshooting }}</textarea>
            {% else %}
                <label>Issue Title: *</label>
                <input type="text" name="issue_title" value="{{ issue_title }}" required>

                <label>Product:</label>
                <input type="text" value="{{ product }}" class="readonly" readonly>

                <label>Issue Description: *</label>
                <textarea name="issue_description" required>{{ issue_description }}</textarea>

                <label>Troubleshooting Steps: *</label>
                <textarea name="troubleshooting_steps" required>{{ troubleshooting_steps }}</textarea>
            {% endif %}

            <button type="submit">📤 Submit Revised Request</button>
        </form>
    </div>
</body>
</html>
'''

VERIFICATION_FORM_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Verify KB Article</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 700px;
            margin: 30px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #4CAF50;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }
        .info-box {
            background-color: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin: 20px 0;
        }
        .kb-link {
            background-color: #f0f0f0;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
            text-align: center;
        }
        .kb-link a {
            color: #d71921;
            text-decoration: none;
            font-weight: bold;
            font-size: 18px;
        }
        .kb-link a:hover {
            text-decoration: underline;
        }
        label {
            display: block;
            margin-top: 20px;
            font-weight: bold;
            color: #333;
        }
        textarea {
            width: 100%;
            padding: 10px;
            margin-top: 5px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-family: Arial, sans-serif;
            min-height: 100px;
            box-sizing: border-box;
        }
        .radio-group {
            margin: 15px 0;
        }
        .radio-option {
            display: inline-block;
            margin-right: 30px;
            padding: 10px 20px;
            border: 2px solid #ddd;
            border-radius: 4px;
            cursor: pointer;
        }
        .radio-option:hover {
            background-color: #f0f0f0;
        }
        .radio-option input[type="radio"] {
            margin-right: 8px;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            margin-top: 20px;
        }
        button:hover {
            background-color: #45a049;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>✅ Verify KB Article</h1>

        <div class="info-box">
            <strong>Request ID:</strong> {{ request_id }}
        </div>

        <div class="kb-link">
            <p><strong>📄 KB Article Created:</strong></p>
            <a href="{{ kb_link }}" target="_blank">{{ kb_link }}</a>
            <p style="font-size: 12px; color: #666; margin-top: 10px;">
                Click to open in new tab and review the KB article
            </p>
        </div>

        <form method="POST">
            <label>Is the KB article correct and complete? *</label>
            <div class="radio-group">
                <label class="radio-option">
                    <input type="radio" name="verification_status" value="correct" required>
                    ✅ Yes, everything looks good
                </label>
                <label class="radio-option">
                    <input type="radio" name="verification_status" value="incorrect" required>
                    ❌ No, needs revision
                </label>
            </div>

            <label>Comments (optional):</label>
            <textarea name="comments" placeholder="Add any comments or feedback about the KB article..."></textarea>

            <button type="submit">📤 Submit Verification</button>
        </form>
    </div>
</body>
</html>
'''

if __name__ == '__main__':
    # For local testing
    print("\n" + "="*60)
    print("KB Assist API Server - Azure SQL Version")
    print("="*60)
    print("Starting on http://0.0.0.0:5000")
    print("Press Ctrl+C to stop")
    print("="*60 + "\n")

    app.run(host='0.0.0.0', port=5000, debug=True)
