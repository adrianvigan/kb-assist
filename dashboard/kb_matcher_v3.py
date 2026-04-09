"""
KB Matcher V3 - Ultimate Version
Combines all matching strategies for maximum accuracy
"""
import sqlite3
import os
import re
from collections import Counter
from product_aliases import get_product_aliases, is_same_product
from kb_matcher import extract_keywords, parse_perts_sections, simple_stem
from semantic_phrases import find_matching_phrases, calculate_phrase_similarity

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'kb_assist.db')


def extract_error_message(perts_text):
    """Extract error message from PERTS"""
    if not perts_text:
        return None

    lines = perts_text.split('\n')
    in_error = False
    error_text = []

    for line in lines:
        if 'ERROR_MESSAGE' in line.upper() or 'ERROR MESSAGE' in line.upper():
            in_error = True
            continue
        elif in_error and any(x in line.upper() for x in ['ROOT_CAUSE', 'TROUBLESHOOTING', 'SOLUTION', 'PROBLEM']):
            break
        elif in_error and line.strip() and line.strip().lower() not in ['n/a', 'na', 'none']:
            error_text.append(line.strip())

    if error_text:
        return ' '.join(error_text)
    return None


def extract_problem_description(perts_text):
    """Extract problem description from PERTS"""
    if not perts_text:
        return ""

    lines = perts_text.split('\n')
    in_problem = False
    problem_text = []

    for line in lines:
        if 'PROBLEM_DESCRIPTION' in line.upper() or 'PROBLEM DESCRIPTION' in line.upper():
            in_problem = True
            continue
        elif in_problem and any(x in line.upper() for x in ['ERROR_MESSAGE', 'ROOT_CAUSE', 'TROUBLESHOOTING']):
            break
        elif in_problem and line.strip():
            problem_text.append(line.strip())

    return ' '.join(problem_text)


def get_problem_category_from_perts(perts_text):
    """
    Infer problem category from PERTS content
    Returns: Install/Uninstall, Performance, Connection, Security, etc.
    """
    if not perts_text:
        return None

    text_lower = perts_text.lower()

    # Category keywords
    categories = {
        'Install / Uninstall': ['install', 'uninstall', 'setup', 'removal', 'reinstall', 'installation'],
        'Performance': ['slow', 'freeze', 'hang', 'lag', 'crash', 'cpu', 'memory', 'performance'],
        'Connection': ['connect', 'disconnect', 'network', 'internet', 'wifi', 'vpn', 'connection'],
        'Activation / License': ['activate', 'activation', 'license', 'subscription', 'expired', 'invalid'],
        'Scanning': ['scan', 'scanning', 'quarantine', 'threat', 'virus', 'malware'],
        'Update': ['update', 'upgrade', 'patch', 'latest version'],
        'Using the Product': ['feature', 'setting', 'configure', 'option', 'how to'],
    }

    category_scores = {}
    for category, keywords in categories.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            category_scores[category] = score

    if category_scores:
        # Return category with highest score
        return max(category_scores, key=category_scores.get)

    return None


def calculate_ultimate_score(product, issue_description, perts_text, kb_title, kb_content, kb_product=None, kb_category=None):
    """
    Ultimate scoring combining ALL strategies

    Scoring Breakdown (120 points max, normalized to 100):
    1. Error Message Exact Match: 25 points
    2. Semantic Phrase Matching: 35 points (30 if in title, 15 if in content)
    3. Product + Category Match: 20 points (15 product + 5 category)
    4. Symptom/Problem Match: 20 points (18 title + 2 content)
    5. Action Keywords Match: 10 points
    6. Solution Match: 10 points

    Total: 120 points max (scaled to 100 for display)
    """
    score = 0.0

    # Parse PERTS
    perts_sections = parse_perts_sections(perts_text)
    problem_desc = extract_problem_description(perts_text)
    error_msg = extract_error_message(perts_text)

    # Extract keywords
    problem_keywords = set(extract_keywords(problem_desc))
    solution_keywords = set(extract_keywords(perts_sections.get('solution', '')))

    # KB content processing
    kb_content_clean = re.sub(r'<[^>]+>', ' ', kb_content)  # Strip HTML
    kb_title_lower = kb_title.lower()
    kb_content_lower = kb_content_clean.lower()
    kb_title_keywords = set(extract_keywords(kb_title))
    kb_content_keywords = set(extract_keywords(kb_content_clean[:2500]))

    # =======================================================================
    # 1. ERROR MESSAGE EXACT MATCH (25 points) - HIGHEST PRIORITY
    # =======================================================================
    if error_msg and len(error_msg) > 5:  # Valid error message
        # Check for exact or very close match
        error_normalized = error_msg.lower().strip()

        # Exact match in content
        if error_normalized in kb_content_lower:
            score += 25
        # Partial match (at least 80% of error message words match)
        else:
            error_words = set(error_normalized.split())
            error_words = {w for w in error_words if len(w) > 3}  # Filter short words
            if error_words:
                # Count how many error words appear in KB
                matches = sum(1 for word in error_words if word in kb_content_lower)
                match_ratio = matches / len(error_words)
                if match_ratio >= 0.8:
                    score += 20
                elif match_ratio >= 0.5:
                    score += 10

    # =======================================================================
    # 2. SEMANTIC PHRASE MATCHING (35 points) - INCREASED FROM 20
    # =======================================================================
    # Find phrases in PERTS
    perts_phrases = find_matching_phrases(perts_text + ' ' + issue_description + ' ' + problem_desc)

    # Find phrases in KB
    kb_phrases = find_matching_phrases(kb_title + ' ' + kb_content_clean[:1500])

    # Calculate overlap
    phrase_overlap = set(perts_phrases).intersection(set(kb_phrases))
    if phrase_overlap:
        # Check if phrase appears in KB TITLE (worth more!)
        kb_title_phrases = find_matching_phrases(kb_title)
        title_phrase_overlap = set(perts_phrases).intersection(set(kb_title_phrases))

        if title_phrase_overlap:
            # Phrase in title = 30 points per phrase (VERY strong signal!)
            # If the KB title contains the exact problem phrase, that's gold!
            phrase_score = min(len(title_phrase_overlap) * 30, 35)
            score += phrase_score
        else:
            # Phrase only in content = 15 points
            phrase_score = min(len(phrase_overlap) * 15, 35)
            score += phrase_score

    # =======================================================================
    # 3. PRODUCT + CATEGORY MATCH (20 points)
    # =======================================================================
    # Product match (15 points)
    if product and kb_product:
        if is_same_product(product, kb_product):
            score += 15
        else:
            # Partial match
            product_keywords = set(extract_keywords(product))
            kb_product_keywords = set(extract_keywords(kb_product))
            overlap = product_keywords.intersection(kb_product_keywords)
            if overlap:
                score += min(len(overlap) * 4, 10)

    # Category match (5 points)
    if kb_category and kb_category.lower() != 'unknown':
        # Infer category from PERTS
        inferred_category = get_problem_category_from_perts(perts_text)
        if inferred_category and inferred_category.lower() == kb_category.lower():
            score += 5
        elif inferred_category:
            # Partial category match (similar categories)
            inferred_kw = set(extract_keywords(inferred_category))
            kb_cat_kw = set(extract_keywords(kb_category))
            if inferred_kw.intersection(kb_cat_kw):
                score += 3

    # =======================================================================
    # 4. SYMPTOM/PROBLEM MATCH (20 points) - INCREASED FROM 15
    # =======================================================================
    # Problem description in title (very important!)
    problem_in_title = problem_keywords.intersection(kb_title_keywords)
    if problem_in_title:
        score += min(len(problem_in_title) * 6, 18)  # Increased from 5 to 6

    # Problem description in content
    problem_in_content = problem_keywords.intersection(kb_content_keywords)
    if problem_in_content:
        score += min(len(problem_in_content) * 0.5, 2)  # Reduced from 1 to 0.5

    # =======================================================================
    # 5. ACTION KEYWORDS MATCH (10 points)
    # =======================================================================
    # Common action verbs
    action_verbs = {'disconnect', 'reconnect', 'connect', 'uninstall', 'install',
                    'restart', 'update', 'enable', 'disable', 'turn', 'click'}

    troubleshooting_kw = set(extract_keywords(perts_sections.get('troubleshooting', '')))
    actions_in_perts = troubleshooting_kw.intersection(action_verbs)
    actions_in_kb = kb_content_keywords.intersection(action_verbs)

    action_overlap = actions_in_perts.intersection(actions_in_kb)
    if action_overlap:
        score += min(len(action_overlap) * 3, 10)

    # =======================================================================
    # 6. SOLUTION MATCH (10 points)
    # =======================================================================
    solution_in_content = solution_keywords.intersection(kb_content_keywords)
    if solution_in_content:
        score += min(len(solution_in_content) * 2, 10)

    # Normalize to 100-point scale (max possible is 120)
    # Scale: score * (100/120) to normalize
    normalized_score = min((score * 100) / 120, 100)

    return round(normalized_score, 1)


def find_matching_kb_v3(product, issue_description, perts_text, top_n=5, min_score=15):
    """
    Ultimate KB Matcher V3

    Combines:
    - Error message exact matching
    - Semantic phrase matching
    - Product aliases
    - Category filtering
    - Symptom-based matching
    - Action keyword matching
    - Solution matching

    Args:
        product: Product name
        issue_description: Issue description
        perts_text: PERTS troubleshooting text
        top_n: Number of results to return
        min_score: Minimum score threshold

    Returns:
        List of matching KBs with scores
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get product aliases
    product_aliases = get_product_aliases(product) if product else []

    # Infer problem category from PERTS
    inferred_category = get_problem_category_from_perts(perts_text)

    # Build WHERE clause
    where_conditions = ["content IS NOT NULL", "LENGTH(content) > 100"]

    # Product filtering (with aliases)
    if product_aliases:
        product_conditions = []
        for alias in product_aliases:
            product_conditions.append(f"product LIKE '%{alias}%'")
            alias_parts = alias.replace('-', ' ').split()
            for part in alias_parts:
                if len(part) >= 3:
                    product_conditions.append(f"(title LIKE '%{part}%' OR content LIKE '%{part}%')")

        where_conditions.append(f"({' OR '.join(product_conditions)})")

    # Category filtering (if inferred) - Make it flexible, don't exclude too much
    # Only use category as a SCORING boost, not as a hard filter
    # This allows cross-category matches (e.g., "Connection" issue might be in "Performance" KB)

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

    # Calculate ultimate score for each KB
    matches = []
    for kb in kb_articles:
        kb_num, title, content, url, category, kb_product = kb

        # Calculate score
        relevance_score = calculate_ultimate_score(
            product,
            issue_description,
            perts_text,
            title,
            content,
            kb_product=kb_product,
            kb_category=category
        )

        # Only include if above threshold
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
