"""
Auto-import reports from Downloads folder
Watches for kb_assist_report_*.json files and imports them to database
"""
import os
import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'kb_assist.db')

# Downloads folder - Windows path
DOWNLOADS_FOLDER = os.path.expanduser('~/Downloads')

def import_report(json_file):
    """Import a single report JSON file into the database"""
    print(f"[Import] Processing: {json_file}")

    try:
        # Read JSON file
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract fields
        case_number = data.get('case_number', 'N/A')
        case_title = data.get('case_title')
        case_status = data.get('case_status')
        case_substatus = data.get('case_substatus')
        product = data.get('product', 'Unknown')
        product_version = data.get('product_version')
        os_name = data.get('os')
        problem_category = data.get('problem_category')
        subcategory = data.get('subcategory')
        kb_article_link = data.get('kb_article_link')
        report_type = data.get('report_type', 'unknown')
        new_troubleshooting = data.get('new_troubleshooting', '')
        engineer_name = data.get('engineer_name', 'Unknown')
        timestamp = data.get('timestamp', datetime.now().isoformat())

        # Map report type to what_failed
        what_failed = None
        if report_type == 'kb_update_request':
            what_failed = f"kb_update_request: {case_title or case_number}"

        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Insert into engineer_reports
        cursor.execute('''
            INSERT INTO engineer_reports (
                case_number, case_title, case_status, case_substatus,
                product, product_version, os, problem_category, subcategory,
                kb_article_link, report_type, what_failed, new_troubleshooting,
                engineer_name, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            case_number, case_title, case_status, case_substatus,
            product, product_version, os_name, problem_category, subcategory,
            kb_article_link, report_type, what_failed, new_troubleshooting,
            engineer_name, timestamp
        ))

        report_id = cursor.lastrowid

        # Create update/new KB requests based on report type
        if product:
            if report_type == 'kb_update_request':
                cursor.execute('''
                    INSERT INTO kb_update_requests (
                        product, issue_description, new_troubleshooting,
                        submitted_by, submitted_date, priority, status,
                        related_report_ids
                    ) VALUES (?, ?, ?, ?, ?, 'medium', 'pending', ?)
                ''', (product, what_failed or case_title, new_troubleshooting,
                      engineer_name, timestamp, str(report_id)))

            elif report_type == 'no_kb_exists':
                cursor.execute('''
                    INSERT INTO new_kb_requests (
                        product, issue_title, issue_description, troubleshooting_steps,
                        submitted_by, submitted_date, priority, status,
                        related_report_ids
                    ) VALUES (?, ?, ?, ?, ?, ?, 'high', 'pending', ?)
                ''', (product, case_title or f"Case {case_number}",
                      new_troubleshooting, new_troubleshooting,
                      engineer_name, timestamp, str(report_id)))

        conn.commit()
        conn.close()

        print(f"[Import] ✓ Successfully imported report {report_id} for case {case_number}")

        # Move file to processed folder
        processed_folder = os.path.join(DOWNLOADS_FOLDER, 'kb_assist_imported')
        os.makedirs(processed_folder, exist_ok=True)

        new_path = os.path.join(processed_folder, os.path.basename(json_file))
        os.rename(json_file, new_path)
        print(f"[Import] Moved to: {new_path}")

        return True

    except Exception as e:
        print(f"[Import] ✗ Error importing {json_file}: {e}")
        return False

def watch_downloads():
    """Watch Downloads folder for new report files"""
    print(f"[Import] Watching Downloads folder: {DOWNLOADS_FOLDER}")
    print("[Import] Press Ctrl+C to stop")

    processed_files = set()

    while True:
        try:
            # Find all kb_assist_report_*.json files
            pattern = "kb_assist_report_*.json"
            files = list(Path(DOWNLOADS_FOLDER).glob(pattern))

            for file_path in files:
                file_str = str(file_path)
                if file_str not in processed_files:
                    # Wait a moment to ensure file is completely written
                    time.sleep(0.5)

                    if import_report(file_str):
                        processed_files.add(file_str)

            # Sleep before next check
            time.sleep(2)

        except KeyboardInterrupt:
            print("\n[Import] Stopped watching")
            break
        except Exception as e:
            print(f"[Import] Error in watch loop: {e}")
            time.sleep(5)

if __name__ == '__main__':
    watch_downloads()
