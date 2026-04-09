"""
Enhanced KB Matcher with Multi-Strategy Approach
Combines multiple matching strategies for better accuracy
"""
import sqlite3
import os
import re
from collections import Counter
from product_aliases import get_product_aliases, is_same_product
from kb_matcher import extract_keywords, parse_perts_sections, simple_stem

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'kb_assist.db')

# Stop words
STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
    'is', 'was', 'are', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did',
    'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that',
    'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which',
    'who', 'when', 'where', 'why', 'how', 'n/a', 'na', 'cx', 'ra', 'issue', 'error'
}


def extract_symptom_keywords(perts_text):
    """
    Extract the SYMPTOM/PROBLEM from PERTS
    This is what the customer is experiencing, not what the engineer tried
    """
    if not perts_text:
        return []

    symptom_keywords = []

    # Look for problem description
    if 'PROBLEM_DESCRIPTION' in perts_text or 'PROBLEM DESCRIPTION' in perts_text:
        lines = perts_text.split('\n')
        in_problem = False
        problem_text = []

        for line in lines:
            if 'PROBLEM_DESCRIPTION' in line.upper():
                in_problem = True
                continue
            elif in_problem and any(x in line.upper() for x in ['ERROR_MESSAGE', 'ROOT_CAUSE', 'TROUBLESHOOTING']):
                break
            elif in_problem:
                problem_text.append(line)

        if problem_text:
            symptom_keywords = extract_keywords(' '.join(problem_text))

    # Also extract from ROOT_CAUSE
    if 'ROOT_CAUSE' in perts_text:
        lines = perts_text.split('\n')
        in_cause = False
        cause_text = []

        for line in lines:
            if 'ROOT_CAUSE' in line.upper() or 'ROOT CAUSE' in line.upper():
                in_cause = True
                continue
            elif in_cause and any(x in line.upper() for x in ['TROUBLESHOOTING', 'SOLUTION']):
                break
            elif in_cause:
                cause_text.append(line)

        if cause_text:
            symptom_keywords.extend(extract_keywords(' '.join(cause_text)))

    return list(set(symptom_keywords))


def extract_action_keywords(perts_text):
    """
    Extract ACTION keywords from troubleshooting steps
    These are verbs: disconnect, reconnect, uninstall, install, click, etc.
    """
    if not perts_text:
        return []

    # Common action verbs in troubleshooting
    action_verbs = {
        'disconnect', 'reconnect', 'connect', 'uninstall', 'install', 'reinstall',
        'restart', 'reboot', 'reset', 'update', 'upgrade', 'downgrade',
        'enable', 'disable', 'turn', 'toggle', 'activate', 'deactivate',
        'delete', 'remove', 'add', 'create', 'open', 'close', 'click',
        'scan', 'check', 'verify', 'confirm', 'test', 'try'
    }

    # Extract troubleshooting section
    sections = parse_perts_sections(perts_text)
    troubleshooting = sections.get('troubleshooting', '')

    # Extract all keywords
    all_keywords = extract_keywords(troubleshooting)

    # Filter to action verbs
    actions = [kw for kw in all_keywords if kw in action_verbs]

    return actions


def calculate_enhanced_score(product, issue_description, perts_text, kb_title, kb_content, kb_product=None, kb_category=None):
    """
    Enhanced scoring with multiple strategies:

    Strategy 1: Symptom-based matching (40 points)
    - Match what the PROBLEM is, not what was tried
    - Focus on: problem description, root cause, error messages

    Strategy 2: Action-based matching (30 points)
    - Match what ACTIONS appear in both PERTS and KB
    - disconnect, reconnect, uninstall, etc.

    Strategy 3: Product + Category (20 points)
    - Exact product match via aliases
    - Category relevance

    Strategy 4: Solution matching (10 points)
    - What actually worked

    Total: 100 points max
    """
    score = 0.0

    # Parse PERTS sections
    perts_sections = parse_perts_sections(perts_text)

    # Extract different types of keywords
    symptom_keywords = set(extract_symptom_keywords(perts_text))
    action_keywords = set(extract_action_keywords(perts_text))
    solution_keywords = set(extract_keywords(perts_sections.get('solution', '')))

    # KB keywords
    kb_title_lower = kb_title.lower()
    kb_content_lower = kb_content.lower()

    # Strip HTML from KB content
    kb_content_clean = re.sub(r'<[^>]+>', ' ', kb_content)

    kb_title_keywords = set(extract_keywords(kb_title))
    kb_content_keywords = set(extract_keywords(kb_content_clean[:2000]))  # First 2000 chars

    # STRATEGY 1: SYMPTOM-BASED MATCHING (40 points max)
    # Match the PROBLEM/SYMPTOM, not the troubleshooting steps
    symptom_in_title = symptom_keywords.intersection(kb_title_keywords)
    symptom_in_content = symptom_keywords.intersection(kb_content_keywords)

    if symptom_in_title:
        # Symptom appears in KB title = very relevant
        score += min(len(symptom_in_title) * 15, 30)

    if symptom_in_content:
        # Symptom appears in KB content = relevant
        score += min(len(symptom_in_content) * 2, 10)

    # STRATEGY 2: ACTION-BASED MATCHING (30 points max)
    # Match ACTIONS that appear in both troubleshooting and KB
    actions_in_title = action_keywords.intersection(kb_title_keywords)
    actions_in_content = action_keywords.intersection(kb_content_keywords)

    if actions_in_title:
        # Actions in title = strong signal (e.g., "disconnect" in both)
        score += min(len(actions_in_title) * 12, 20)

    if actions_in_content:
        # Actions in content = good signal
        score += min(len(actions_in_content) * 2, 10)

    # STRATEGY 3: PRODUCT + CATEGORY (20 points max)
    # Product match using aliases
    if product and kb_product:
        if is_same_product(product, kb_product):
            score += 15  # Perfect product match
        else:
            # Partial match
            product_keywords = set(extract_keywords(product))
            kb_product_keywords = set(extract_keywords(kb_product))
            overlap = product_keywords.intersection(kb_product_keywords)
            if overlap:
                score += min(len(overlap) * 3, 10)

    # Category match
    if kb_category and kb_category.lower() != 'unknown':
        category_keywords = set(extract_keywords(kb_category))
        if symptom_keywords.intersection(category_keywords) or action_keywords.intersection(category_keywords):
            score += 5

    # STRATEGY 4: SOLUTION MATCHING (10 points max)
    # What actually worked
    solution_in_content = solution_keywords.intersection(kb_content_keywords)
    if solution_in_content:
        score += min(len(solution_in_content) * 2, 10)

    return round(score, 1)


def find_matching_kb_enhanced(product, issue_description, perts_text, top_n=5, min_score=20):
    """
    Enhanced KB matching with multi-strategy approach

    Args:
        product: Product name
        issue_description: Issue description
        perts_text: PERTS troubleshooting text
        top_n: Number of top matches to return
        min_score: Minimum score threshold (default: 20)

    Returns:
        List of matching KBs with enhanced scores
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get product aliases
    product_aliases = get_product_aliases(product) if product else []

    # Build WHERE clause
    where_conditions = ["content IS NOT NULL", "LENGTH(content) > 100"]

    if product_aliases:
        product_conditions = []
        for alias in product_aliases:
            product_conditions.append(f"product LIKE '%{alias}%'")
            alias_parts = alias.replace('-', ' ').split()
            for part in alias_parts:
                if len(part) >= 3:
                    product_conditions.append(f"(title LIKE '%{part}%' OR content LIKE '%{part}%')")

        where_conditions.append(f"({' OR '.join(product_conditions)})")

    query = f"""
        SELECT kb_number, title, content, url, category, product
        FROM kb_articles
        WHERE {' AND '.join(where_conditions)}
    """

    cursor.execute(query)
    kb_articles = cursor.fetchall()
    conn.close()

    if not kb_articles:
        return []

    # Calculate enhanced score for each KB
    matches = []
    for kb in kb_articles:
        kb_num, title, content, url, category, kb_product = kb

        # Calculate enhanced score
        relevance_score = calculate_enhanced_score(
            product,
            issue_description,
            perts_text,
            title,
            content,
            kb_product=kb_product,
            kb_category=category
        )

        # Only include if above minimum threshold
        if relevance_score >= min_score:
            matches.append({
                'kb_number': kb_num,
                'title': title,
                'url': url,
                'category': category,
                'similarity_score': relevance_score,
                'content_preview': content[:200] + '...' if len(content) > 200 else content
            })

    # Sort by score (highest first)
    matches.sort(key=lambda x: x['similarity_score'], reverse=True)

    return matches[:top_n]
