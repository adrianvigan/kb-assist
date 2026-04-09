"""
Duplicate Detection AI
Uses similarity matching to detect potential duplicate submissions
"""
import sqlite3
import os
from difflib import SequenceMatcher
from datetime import datetime, timedelta
import re

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'kb_assist.db')


def normalize_text(text):
    """Normalize text for comparison"""
    if not text:
        return ""

    # Convert to lowercase
    text = text.lower()

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove special characters
    text = re.sub(r'[^\w\s]', '', text)

    return text.strip()


def calculate_similarity(text1, text2):
    """Calculate similarity score between two texts (0-100)"""
    if not text1 or not text2:
        return 0.0

    # Normalize texts
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)

    # Use SequenceMatcher
    ratio = SequenceMatcher(None, norm1, norm2).ratio()

    return round(ratio * 100, 1)


def find_duplicates(
    product,
    case_number=None,
    case_title=None,
    perts_text=None,
    kb_article_link=None,
    report_type=None,
    days_back=7,
    similarity_threshold=70,
    limit=5
):
    """
    Find potential duplicate submissions

    Args:
        product: Product name
        case_number: Case number (optional)
        case_title: Case title (optional)
        perts_text: PERTS/troubleshooting text (optional)
        kb_article_link: KB article link (optional)
        report_type: Report type (optional)
        days_back: Look back N days (default: 7)
        similarity_threshold: Minimum similarity score to consider (default: 70%)
        limit: Max number of duplicates to return (default: 5)

    Returns:
        List of potential duplicate submissions with similarity scores
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Calculate date threshold
    date_threshold = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

    # Build query to find recent submissions for same product
    query = """
        SELECT
            id,
            case_number,
            case_title,
            product,
            report_type,
            new_troubleshooting,
            kb_article_link,
            status,
            engineer_name,
            created_at
        FROM engineer_reports
        WHERE DATE(created_at) >= ?
        AND product = ?
    """

    params = [date_threshold, product]

    # Add report type filter if specified
    if report_type:
        query += " AND report_type = ?"
        params.append(report_type)

    # Execute query
    cursor.execute(query, params)
    candidates = cursor.fetchall()
    conn.close()

    if not candidates:
        return []

    # Calculate similarity for each candidate
    duplicates = []

    for candidate in candidates:
        cand_id, cand_case_num, cand_title, cand_product, cand_type, cand_perts, cand_kb, cand_status, cand_engineer, cand_date = candidate

        # Calculate individual similarity scores
        scores = []

        # 1. Case number match (exact match = 100)
        if case_number and cand_case_num:
            if case_number.lower() == cand_case_num.lower():
                scores.append(100)
            else:
                scores.append(0)

        # 2. Case title similarity
        if case_title and cand_title:
            title_sim = calculate_similarity(case_title, cand_title)
            scores.append(title_sim)

        # 3. PERTS/troubleshooting similarity
        if perts_text and cand_perts:
            perts_sim = calculate_similarity(perts_text, cand_perts)
            scores.append(perts_sim * 1.5)  # Weight PERTS more heavily

        # 4. KB article match (exact match = 100)
        if kb_article_link and cand_kb:
            if kb_article_link.lower() == cand_kb.lower():
                scores.append(100)
            else:
                kb_sim = calculate_similarity(kb_article_link, cand_kb)
                scores.append(kb_sim)

        # Calculate overall similarity (weighted average)
        if scores:
            overall_similarity = sum(scores) / len(scores)
        else:
            overall_similarity = 0

        # Only include if above threshold
        if overall_similarity >= similarity_threshold:
            duplicates.append({
                'id': cand_id,
                'case_number': cand_case_num,
                'case_title': cand_title,
                'product': cand_product,
                'report_type': cand_type,
                'status': cand_status,
                'engineer_name': cand_engineer,
                'submitted_date': cand_date,
                'similarity_score': round(overall_similarity, 1),
                'kb_article_link': cand_kb
            })

    # Sort by similarity score (highest first)
    duplicates.sort(key=lambda x: x['similarity_score'], reverse=True)

    # Return top N matches
    return duplicates[:limit]


def check_for_duplicates_before_approval(report_id):
    """
    Check if a report has potential duplicates before approval

    Args:
        report_id: Report ID to check

    Returns:
        Dict with duplicate detection results
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get report details
    cursor.execute("""
        SELECT
            product, case_number, case_title, new_troubleshooting,
            kb_article_link, report_type
        FROM engineer_reports
        WHERE id = ?
    """, (report_id,))

    report = cursor.fetchone()
    conn.close()

    if not report:
        return {'has_duplicates': False, 'duplicates': []}

    product, case_num, case_title, perts, kb_link, report_type = report

    # Find duplicates
    duplicates = find_duplicates(
        product=product,
        case_number=case_num,
        case_title=case_title,
        perts_text=perts,
        kb_article_link=kb_link,
        report_type=report_type,
        days_back=30,  # Look back 30 days
        similarity_threshold=65,  # Lower threshold for safety
        limit=5
    )

    # Exclude the report itself
    duplicates = [d for d in duplicates if d['id'] != report_id]

    return {
        'has_duplicates': len(duplicates) > 0,
        'duplicate_count': len(duplicates),
        'duplicates': duplicates
    }
