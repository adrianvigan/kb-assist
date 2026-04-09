"""
AI-Powered KB Matcher
Uses keyword extraction and weighted scoring to match engineer reports to existing KB articles
"""
import sqlite3
import os
import re
from collections import Counter
from product_aliases import get_product_aliases, is_same_product

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'kb_assist.db')

# Common words to filter out (stop words)
STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
    'is', 'was', 'are', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did',
    'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that',
    'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which',
    'who', 'when', 'where', 'why', 'how', 'n/a', 'na', 'cx', 'ra', 'issue', 'error'
}


def simple_stem(word):
    """Simple stemming - remove common suffixes"""
    # Remove common suffixes to match word variants
    # (e.g., disconnecting, disconnected, disconnect → disconnect)

    # Special cases for common tech support words
    if word == 'connection':
        return 'connect'
    if word == 'installation':
        return 'install'
    if word == 'configuration':
        return 'config'

    # Order matters - check longer suffixes first
    suffixes = ['tion', 'ing', 'ed', 'es', 's', 'ly', 'er', 'est', 'ment']

    for suffix in suffixes:
        if word.endswith(suffix) and len(word) > len(suffix) + 2:
            stemmed = word[:-len(suffix)]
            # Avoid over-stemming (e.g., "install" shouldn't become "inst")
            if len(stemmed) >= 3:
                return stemmed

    return word


def extract_keywords(text, min_length=3, use_stemming=True):
    """Extract meaningful keywords from text"""
    if not text:
        return []

    # Strip HTML tags if present
    text = re.sub(r'<[^>]+>', ' ', text)

    # Convert to lowercase and extract words
    words = re.findall(r'\b[a-z]+\b', text.lower())

    # Filter stop words and short words
    keywords = [w for w in words if w not in STOP_WORDS and len(w) >= min_length]

    # Apply simple stemming if enabled
    if use_stemming:
        keywords = [simple_stem(w) for w in keywords]

    # Return most common keywords (deduplicated)
    return [word for word, count in Counter(keywords).most_common(30)]


def parse_perts_sections(perts_text):
    """Parse PERTS into sections and extract troubleshooting keywords"""
    if not perts_text:
        return {}

    sections = {
        'problem': '',
        'error': '',
        'root_cause': '',
        'troubleshooting': '',
        'solution': ''
    }

    current_section = None
    lines = perts_text.split('\n')

    for line in lines:
        line_upper = line.strip().upper()

        if 'PROBLEM_DESCRIPTION' in line_upper:
            current_section = 'problem'
        elif 'ERROR_MESSAGE' in line_upper:
            current_section = 'error'
        elif 'ROOT_CAUSE' in line_upper:
            current_section = 'root_cause'
        elif 'TROUBLESHOOTING_STEPS' in line_upper:
            current_section = 'troubleshooting'
        elif 'SOLUTION_THAT_WORKED' in line_upper or 'SOLUTION' in line_upper:
            current_section = 'solution'
        elif current_section and line.strip():
            sections[current_section] += ' ' + line.strip()

    return sections


def calculate_relevance_score(product, issue_description, perts_text, kb_title, kb_content, kb_product=None, kb_category=None):
    """
    Calculate relevance score using weighted keyword matching + PowerBI metadata

    Scoring breakdown:
    - Exact product match (PowerBI): 30 points (NEW - uses metadata!)
    - Core issue keyword match (title): 25 points
    - Category relevance: 15 points (NEW - uses metadata!)
    - Troubleshooting steps match: 15 points
    - Solution match: 10 points
    - Root cause match: 5 points

    Total: 100 points max
    """
    score = 0.0

    # Parse PERTS sections
    perts_sections = parse_perts_sections(perts_text)

    # Extract keywords from different sources
    product_keywords = set(extract_keywords(product))
    issue_keywords = set(extract_keywords(issue_description))
    troubleshooting_keywords = set(extract_keywords(perts_sections.get('troubleshooting', '')))
    solution_keywords = set(extract_keywords(perts_sections.get('solution', '')))
    root_cause_keywords = set(extract_keywords(perts_sections.get('root_cause', '')))
    problem_keywords = set(extract_keywords(perts_sections.get('problem', '')))

    # Combine all issue-related keywords
    all_issue_keywords = issue_keywords | problem_keywords | troubleshooting_keywords | solution_keywords

    # KB keywords
    kb_title_lower = kb_title.lower()
    kb_content_lower = kb_content.lower()
    kb_title_keywords = set(extract_keywords(kb_title))
    kb_content_keywords = set(extract_keywords(kb_content[:1500]))  # First 1500 chars

    # 1. EXACT PRODUCT MATCH (PowerBI metadata + Aliases) - 30 points max
    if product and kb_product:
        # Check if products are the same (using alias mapping)
        if is_same_product(product, kb_product):
            score += 30  # Perfect match (direct or via alias)!
        else:
            # Partial product match (e.g., "VPN" in "PUBLIC WI-FI PROTECTION")
            product_keywords_lower = set([kw.lower() for kw in product_keywords])
            kb_product_keywords = set(extract_keywords(kb_product))
            kb_product_keywords_lower = set([kw.lower() for kw in kb_product_keywords])

            overlap = product_keywords_lower.intersection(kb_product_keywords_lower)
            if overlap:
                score += min(len(overlap) * 8, 20)  # Partial credit

    # 2. CORE ISSUE KEYWORD MATCH IN TITLE (25 points max)
    # This is the most important - if the KB title mentions the core problem, it's likely relevant
    core_title_matches = all_issue_keywords.intersection(kb_title_keywords)

    # Boost for critical action keywords in both title and troubleshooting
    critical_keywords = troubleshooting_keywords.intersection(kb_title_keywords)
    if critical_keywords:
        # These are words that appear in BOTH the troubleshooting steps AND the KB title
        # This is a strong signal (e.g., "disconnect", "reconnect" in both)
        score += min(len(critical_keywords) * 10, 25)  # Increased from 8 to 10

    # Additional boost for any title matches
    if core_title_matches:
        score += min(len(core_title_matches) * 3, 25)  # Increased from 2 to 3

    # 3. CATEGORY RELEVANCE (PowerBI metadata) - 15 points max
    if kb_category and kb_category.lower() != 'unknown':
        # Common categories: "Install / Uninstall", "Performance", "Using the Product", etc.
        category_keywords = set(extract_keywords(kb_category))

        # Check if issue keywords match category
        if all_issue_keywords.intersection(category_keywords):
            score += 15

    # 4. Troubleshooting steps matching in content (15 points max)
    # Match what the engineer actually tried with KB content
    troubleshooting_matches = troubleshooting_keywords.intersection(kb_content_keywords)
    score += min(len(troubleshooting_matches) * 2, 15)

    # 5. Solution matching (10 points max)
    solution_matches = solution_keywords.intersection(kb_content_keywords)
    score += min(len(solution_matches) * 2, 10)

    # 6. Root cause matching (5 points max)
    root_cause_matches = root_cause_keywords.intersection(kb_content_keywords)
    score += min(len(root_cause_matches) * 1, 5)

    return round(score, 1)


def find_matching_kb(product, issue_description, perts_text, top_n=5):
    """
    Find matching KB articles for a given issue using weighted keyword matching

    Args:
        product: Product name
        issue_description: Description of the issue
        perts_text: PERTS troubleshooting text
        top_n: Number of top matches to return

    Returns:
        List of matching KBs with relevance scores
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all product aliases for flexible matching
    product_aliases = get_product_aliases(product) if product else []

    # Build WHERE clause for product matching
    where_conditions = ["content IS NOT NULL", "LENGTH(content) > 100"]

    if product_aliases:
        # Match against any product alias
        product_conditions = []
        for alias in product_aliases:
            # Match in product field OR title OR content
            product_conditions.append(f"product LIKE '%{alias}%'")
            # Also match key terms in title/content
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

    # Calculate relevance score for each KB
    matches = []
    for kb in kb_articles:
        kb_num, title, content, url, category, kb_product = kb

        # Calculate weighted relevance score (now includes PowerBI metadata!)
        relevance_score = calculate_relevance_score(
            product,
            issue_description,
            perts_text,
            title,
            content,
            kb_product=kb_product,
            kb_category=category
        )

        # Only include KBs with score > 5 (some relevance)
        if relevance_score > 5:
            matches.append({
                'kb_number': kb_num,
                'title': title,
                'url': url,
                'category': category,
                'similarity_score': relevance_score,  # Now this is relevance score
                'content_preview': content[:200] + '...' if len(content) > 200 else content
            })

    # Sort by relevance score (highest first)
    matches.sort(key=lambda x: x['similarity_score'], reverse=True)

    # Return top N matches
    return matches[:top_n]


def get_kb_details(kb_number):
    """Get full details of a specific KB article"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT kb_number, title, content, url, product, category, last_updated
        FROM kb_articles
        WHERE kb_number = ?
    """, (kb_number,))

    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            'kb_number': result[0],
            'title': result[1],
            'content': result[2],
            'url': result[3],
            'product': result[4],
            'category': result[5],
            'last_updated': result[6]
        }
    return None
