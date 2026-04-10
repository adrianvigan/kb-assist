"""
AI KB Matcher - Smart Hybrid Approach
Searches 1,331 KB articles to find similar content for new TS submissions

Strategy (Optimized):
1. Keyword filtering (PostgreSQL) - find 0-10 candidates
   - 0 matches → PASS (obviously unique, skip AI)
   - 1-5 matches → AI validation (check if truly similar)
   - 6+ matches → PASS (too generic, skip AI)
2. AI validation (only for 1-5 matches) - check uniqueness
   - Uses existing AI validator (like KB update validator)
   - Returns: unique OR similar with KB links
"""
import os
import sys
import re
import json
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Add database path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'database'))
from azure_db import get_connection

load_dotenv()

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AZURE_OPENAI_KEY = os.getenv('AZURE_OPENAI_API_KEY')
AZURE_OPENAI_DEPLOYMENT = os.getenv('AZURE_OPENAI_DEPLOYMENT', 'kb-assistant')  # Fixed: was looking for wrong env var

# Thresholds
KEYWORD_MATCH_MIN = 1  # Minimum matches to trigger AI
KEYWORD_MATCH_MAX = 5  # Maximum matches to send to AI (6+ = too generic)
AI_CONFIDENCE_THRESHOLD = 0.80  # Only show 80%+ confident matches

class KBMatcher:
    """Smart Hybrid AI KB Matcher"""

    def __init__(self):
        """Initialize AI client if available"""
        self.ai_available = False

        try:
            from openai import AzureOpenAI

            if AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY and AZURE_OPENAI_DEPLOYMENT:
                self.client = AzureOpenAI(
                    azure_endpoint=AZURE_OPENAI_ENDPOINT,
                    api_key=AZURE_OPENAI_KEY,
                    api_version="2024-02-15-preview"
                )
                self.ai_available = True
                print("✅ AI KB Matcher initialized (Smart Hybrid Mode)", flush=True)
            else:
                print("⚠️  Azure OpenAI not configured - using keyword-only matching", flush=True)
        except ImportError:
            print("⚠️  openai package not installed - using keyword-only matching", flush=True)
        except Exception as e:
            print(f"⚠️  AI initialization failed: {e} - using keyword-only matching", flush=True)

    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract important keywords from text"""
        if not text:
            return []

        # Remove common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'may', 'might', 'can', 'this', 'that',
            'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }

        # Extract words (alphanumeric, keep version numbers)
        words = re.findall(r'\b[a-z0-9]+(?:\.[0-9]+)*\b', text.lower())

        # Filter stop words and short words
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        # Count frequency
        word_freq = {}
        for word in keywords:
            word_freq[word] = word_freq.get(word, 0) + 1

        # Sort by frequency, return top N
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:max_keywords]]

    def keyword_search(self, product: str, issue_description: str,
                      troubleshooting: str, limit: int = 10) -> List[Dict]:
        """
        Layer 1: Smart keyword search (product-specific)
        Returns 0-10 candidates max
        """
        print(f"\n🔍 Layer 1: Keyword Search (product: {product})", flush=True)

        # Combine all text for keyword extraction
        combined_text = f"{issue_description} {troubleshooting}"
        keywords = self.extract_keywords(combined_text, max_keywords=10)

        if not keywords:
            print("⚠️  No keywords extracted", flush=True)
            return []

        print(f"📌 Top keywords: {', '.join(keywords[:3])}...", flush=True)

        conn = get_connection()
        cursor = conn.cursor()

        # Search ONLY within the same product (more accurate!)
        # Use top 5 keywords for matching
        search_conditions = []
        params = [f"%{product}%"]  # Product filter

        for keyword in keywords[:5]:
            search_conditions.append("(title ILIKE %s OR content ILIKE %s)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        where_clause = " OR ".join(search_conditions) if search_conditions else "1=0"

        query = f"""
            SELECT
                kb_number,
                title,
                product,
                url,
                LEFT(content, 500) as content_preview,
                (
                    (CASE WHEN title ILIKE %s THEN 10 ELSE 0 END) +
                    (CASE WHEN title ILIKE %s THEN 5 ELSE 0 END) +
                    (CASE WHEN content ILIKE %s THEN 3 ELSE 0 END)
                ) as relevance_score
            FROM kb_articles
            WHERE product ILIKE %s
              AND ({where_clause})
            ORDER BY relevance_score DESC
            LIMIT %s
        """

        # Scoring params (use top 3 keywords for scoring)
        top_keywords = keywords[:3] + [''] * (3 - len(keywords[:3]))  # Pad to 3
        score_params = [f"%{top_keywords[0]}%", f"%{top_keywords[1]}%", f"%{top_keywords[2]}%"]

        cursor.execute(query, score_params + params + [limit])
        results = cursor.fetchall()
        conn.close()

        print(f"✅ Found {len(results)} product-specific matches", flush=True)

        # Convert to list of dicts
        candidates = []
        for row in results:
            candidates.append({
                'kb_number': row[0],
                'title': row[1],
                'product': row[2],
                'url': row[3],
                'content_preview': row[4],
                'keyword_score': row[5]
            })

        return candidates

    def ai_validate_uniqueness(self, issue_description: str, troubleshooting: str,
                              candidates: List[Dict]) -> Dict:
        """
        Layer 2: AI validation (only called if 1-5 keyword matches)
        Uses GPT-4o to determine if submission is truly unique or similar

        Returns:
            {
                'is_unique': True/False,
                'similar_kbs': [...],  # Empty if unique
                'reasoning': 'Why AI thinks this'
            }
        """
        if not self.ai_available:
            print("⚠️  AI not available, treating as unique", flush=True)
            return {
                'is_unique': True,
                'similar_kbs': [],
                'reasoning': 'AI validation not available'
            }

        print(f"\n🤖 Layer 2: AI Validation ({len(candidates)} candidates)", flush=True)

        try:
            # Build KB summaries for AI
            kb_summaries = []
            for idx, kb in enumerate(candidates, 1):
                kb_summaries.append(f"""
KB-{kb['kb_number']}: {kb['title']}
Product: {kb['product']}
Preview: {kb['content_preview'][:200]}...
URL: {kb['url']}
""")

            prompt = f"""You are a KB duplicate detector. Analyze if a new troubleshooting submission is UNIQUE or SIMILAR to existing KB articles.

NEW SUBMISSION:
Issue: {issue_description}
Troubleshooting Steps: {troubleshooting}

EXISTING KBs TO COMPARE:
{chr(10).join(kb_summaries)}

TASK:
Determine if the new submission describes a UNIQUE solution not covered by existing KBs, or if it's SIMILAR to one or more existing KBs.

RULES:
- If the solution/workaround is DIFFERENT, mark as UNIQUE
- If the solution is the SAME or very similar, mark as SIMILAR
- Consider: Does the existing KB already cover this fix?
- Minor wording differences don't matter - focus on the SOLUTION itself

Respond in JSON format:
{{
    "is_unique": true or false,
    "similar_kb_numbers": ["11005", "8234"],  // Empty array if unique
    "confidence": 0.85,  // 0-1 scale
    "reasoning": "Brief explanation of your decision"
}}"""

            response = self.client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": "You are a technical KB duplicate detector. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            result_text = response.choices[0].message.content.strip()

            # Extract JSON from response
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0].strip()

            ai_result = json.loads(result_text)

            is_unique = ai_result.get('is_unique', True)
            similar_kb_nums = ai_result.get('similar_kb_numbers', [])
            confidence = ai_result.get('confidence', 0.5)
            reasoning = ai_result.get('reasoning', 'No reasoning provided')

            print(f"✅ AI Decision: {'UNIQUE' if is_unique else 'SIMILAR'} (confidence: {confidence:.0%})", flush=True)
            print(f"   Reasoning: {reasoning[:100]}...", flush=True)

            # Build similar_kbs list with full details
            similar_kbs = []
            if not is_unique and similar_kb_nums:
                for kb in candidates:
                    if kb['kb_number'] in similar_kb_nums and confidence >= AI_CONFIDENCE_THRESHOLD:
                        similar_kbs.append({
                            'kb_number': kb['kb_number'],
                            'title': kb['title'],
                            'url': kb['url'],
                            'product': kb['product'],
                            'confidence': confidence,
                            'reason': reasoning[:200]  # Truncate for display
                        })

                print(f"   Found {len(similar_kbs)} high-confidence matches (≥80%)", flush=True)

            return {
                'is_unique': is_unique or len(similar_kbs) == 0,  # Treat as unique if no high-confidence matches
                'similar_kbs': similar_kbs,
                'reasoning': reasoning
            }

        except Exception as e:
            print(f"⚠️  AI validation failed: {e}", flush=True)
            import traceback
            traceback.print_exc()

            # Fallback: treat as unique (safe default)
            return {
                'is_unique': True,
                'similar_kbs': [],
                'reasoning': f'AI validation error: {str(e)}'
            }


    def find_similar_kbs(self, product: str, issue_description: str,
                        troubleshooting_steps: str) -> Dict:
        """
        Smart Hybrid KB Matching

        Layer 1: Keyword search (0-10 product-specific matches)
        Layer 2: AI validation (only if 1-5 matches found)

        Returns:
            {
                'status': 'complete' | 'failed',
                'decision': 'unique' | 'similar' | 'skipped_ai',
                'similar_kbs': [...]  # Empty if unique
            }
        """
        print("="*80, flush=True)
        print("🔍 SMART HYBRID KB MATCHER", flush=True)
        print("="*80, flush=True)
        print(f"Product: {product}", flush=True)
        print(f"Issue: {issue_description[:80]}...", flush=True)
        print("="*80, flush=True)

        try:
            # Layer 1: Keyword search (product-specific, max 10 results)
            keyword_matches = self.keyword_search(
                product=product,
                issue_description=issue_description,
                troubleshooting=troubleshooting_steps,
                limit=10
            )

            match_count = len(keyword_matches)

            # Decision tree based on keyword matches
            if match_count == 0:
                # No keyword matches → Obviously unique, skip AI
                print("✅ Decision: UNIQUE (no keyword matches, AI skipped)", flush=True)
                print("="*80, flush=True)
                return {
                    'status': 'complete',
                    'decision': 'unique',
                    'similar_kbs': [],
                    'reasoning': 'No similar keywords found in existing KBs'
                }

            elif match_count >= KEYWORD_MATCH_MIN and match_count <= KEYWORD_MATCH_MAX:
                # 1-5 matches → Send to AI for validation
                print(f"⚠️  Found {match_count} keyword matches → Sending to AI", flush=True)

                ai_result = self.ai_validate_uniqueness(
                    issue_description=issue_description,
                    troubleshooting=troubleshooting_steps,
                    candidates=keyword_matches
                )

                if ai_result['is_unique']:
                    print("✅ Decision: UNIQUE (AI validated - different solution)", flush=True)
                    print("="*80, flush=True)
                    return {
                        'status': 'complete',
                        'decision': 'unique',
                        'similar_kbs': [],
                        'reasoning': ai_result['reasoning']
                    }
                else:
                    similar_count = len(ai_result['similar_kbs'])
                    print(f"⚠️  Decision: SIMILAR (AI found {similar_count} matching KB(s))", flush=True)
                    print("="*80, flush=True)
                    return {
                        'status': 'complete',
                        'decision': 'similar',
                        'similar_kbs': ai_result['similar_kbs'],
                        'reasoning': ai_result['reasoning']
                    }

            else:
                # 6+ matches → Too generic/noisy, skip AI
                print(f"⚠️  Found {match_count} matches (too generic) → AI skipped", flush=True)
                print("✅ Decision: UNIQUE (keywords too common, likely unique issue)", flush=True)
                print("="*80, flush=True)
                return {
                    'status': 'complete',
                    'decision': 'skipped_ai',
                    'similar_kbs': [],
                    'reasoning': 'Too many generic keyword matches - treating as unique'
                }

        except Exception as e:
            print(f"❌ Matching failed: {e}", flush=True)
            import traceback
            traceback.print_exc()

            # Safe fallback: treat as unique
            return {
                'status': 'failed',
                'decision': 'unique',
                'similar_kbs': [],
                'reasoning': f'Error during matching: {str(e)}'
            }


if __name__ == '__main__':
    # Test the matcher
    print("Testing AI KB Matcher...\n")

    matcher = KBMatcher()

    result = matcher.find_similar_kbs(
        product="Apex One",
        issue_description="Agent not scanning files after installation",
        troubleshooting_steps="Restarted the agent service and verified configuration",
        top_n=3
    )

    print(f"\nResult: {json.dumps(result, indent=2)}")
