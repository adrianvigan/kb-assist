"""
AI KB Draft Generator
Uses Azure OpenAI to generate KB drafts from engineer reports
Follows Trend Micro KB format learned from scraped articles
"""
import os
import sys
from openai import AzureOpenAI
from dotenv import load_dotenv
import json
from datetime import datetime

# Import PostgreSQL connection
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'database'))
from azure_db import get_connection

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Load environment variables
load_dotenv()

# Azure OpenAI Configuration
AZURE_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AZURE_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
AZURE_DEPLOYMENT = os.getenv('AZURE_OPENAI_DEPLOYMENT')
API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')

class KBGenerator:
    def __init__(self):
        """Initialize Azure OpenAI client"""
        if not all([AZURE_ENDPOINT, AZURE_API_KEY, AZURE_DEPLOYMENT]):
            raise ValueError(
                "Missing Azure OpenAI credentials. "
                "Please create .env file with AZURE_OPENAI_ENDPOINT, "
                "AZURE_OPENAI_API_KEY, and AZURE_OPENAI_DEPLOYMENT"
            )

        self.client = AzureOpenAI(
            azure_endpoint=AZURE_ENDPOINT,
            api_key=AZURE_API_KEY,
            api_version=API_VERSION
        )
        self.deployment = AZURE_DEPLOYMENT

    def get_kb_examples(self, product=None, limit=5):
        """Get sample KB articles to teach AI the format"""
        conn = get_connection()
        cursor = conn.cursor()

        if product:
            query = '''
                SELECT title, content, article_html
                FROM kb_articles
                WHERE product = %s
                AND length(content) > 500
                ORDER BY RANDOM()
                LIMIT %s
            '''
            cursor.execute(query, (product, limit))
        else:
            query = '''
                SELECT title, content, article_html
                FROM kb_articles
                WHERE length(content) > 500
                ORDER BY RANDOM()
                LIMIT %s
            '''
            cursor.execute(query, (limit,))

        examples = cursor.fetchall()
        conn.close()

        return examples

    def get_report_data(self, report_id):
        """Get engineer report data"""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT case_number, case_title, case_status, case_substatus,
                   product, product_version, os, problem_category, subcategory,
                   report_type, new_troubleshooting, engineer_name, created_at, engineer_notes
            FROM engineer_reports
            WHERE id = %s
        ''', (report_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            'case_number': row[0],
            'case_title': row[1],
            'case_status': row[2],
            'case_substatus': row[3],
            'product': row[4],
            'product_version': row[5],
            'os': row[6],
            'problem_category': row[7],
            'subcategory': row[8],
            'report_type': row[9],
            'perts': row[10],
            'engineer': row[11],
            'date': row[12],
            'engineer_notes': row[13]
        }

    def generate_kb_draft(self, report_id):
        """
        Generate KB draft from engineer report

        Returns:
            dict with 'title', 'content', 'metadata', 'confidence'
        """
        print(f"\n🤖 Generating KB draft for Report ID: {report_id}")

        # Get report data
        report = self.get_report_data(report_id)
        if not report:
            return {"error": "Report not found"}

        print(f"   Case: {report['case_number']}")
        print(f"   Product: {report['product']}")

        # Get KB examples for context
        kb_examples = self.get_kb_examples(product=report['product'], limit=3)
        print(f"   Found {len(kb_examples)} example KBs for reference")

        # Build prompt
        prompt = self._build_prompt(report, kb_examples)

        # Call Azure OpenAI
        print("   🔄 Calling Azure OpenAI...")
        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert technical writer for Trend Micro. "
                                 "You create clear, structured KB articles following Trend Micro's format. "
                                 "You write in professional technical English, using active voice and clear steps."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower = more consistent
                max_tokens=2000
            )

            kb_draft = response.choices[0].message.content
            print("   ✅ KB draft generated successfully")

            return {
                'success': True,
                'title': self._extract_title(kb_draft),
                'content': kb_draft,
                'metadata': {
                    'case_number': report['case_number'],
                    'product': report['product'],
                    'category': report['problem_category'],
                    'subcategory': report['subcategory'],
                    'generated_at': datetime.now().isoformat(),
                    'engineer': report['engineer']
                },
                'tokens_used': response.usage.total_tokens,
                'model': self.deployment
            }

        except Exception as e:
            print(f"   ❌ Error: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _build_prompt(self, report, kb_examples):
        """Build the prompt for AI"""
        # Format KB examples
        examples_text = "\n\n---\n\n".join([
            f"Example KB:\nTitle: {ex[0]}\n\nContent:\n{ex[1][:1500]}..."
            for ex in kb_examples[:3]  # Use 3 examples to learn the pattern
        ])

        prompt = f"""You are a Trend Micro KB article writer. Study the examples below to learn the exact format and style.

REFERENCE KB ARTICLES (STUDY THESE CAREFULLY - follow this EXACT format and tone):
{examples_text}

---

ENGINEER REPORT DATA:
Case Number: {report['case_number']}
Case Title: {report['case_title']}
Product: {report['product']} {report['product_version'] or ''}
OS: {report['os'] or 'Not specified'}
Problem Category: {report['problem_category']}
Subcategory: {report['subcategory']}

ENGINEER'S QUICK SUMMARY:
{report.get('engineer_notes') or 'Not provided'}

TROUBLESHOOTING STEPS (PERTS):
{report['perts']}

---

TASK:
Create a customer-facing KB article following the EXACT Trend Micro format shown in the examples above.

REQUIRED STRUCTURE (match the examples exactly):

1. **Title**: Short, descriptive problem statement (e.g., "Product X keeps doing Y after Z")

2. **Opening Sentence**: One clear sentence describing the problem behavior

3. **"Why did this happen?" Section**:
   - Use bullet points (•)
   - List 2-3 possible root causes
   - Keep it simple and customer-friendly

4. **"What should I do next?" Section**:
   - Use numbered steps (1., 2., 3.)
   - Each step should have:
     • A brief description of what to do
     • Sub-bullets with exact UI navigation (Click on X, Select Y, etc.)
     • "Try [action] again" at the end of each step
   - Include conditional logic: "If X happens, do Y"
   - Final troubleshooting step if previous steps don't work

CRITICAL REQUIREMENTS:
- Use the EXACT section headers: "Why did this happen?" and "What should I do next?"
- Use bullet points (•) for causes, NOT numbered lists
- Use numbered lists (1., 2., 3.) for solutions
- Use sub-bullets (•) under each numbered step for detailed actions
- Write in friendly, customer-facing language (avoid technical jargon)
- Include specific UI navigation (Click on Settings, Toggle off X, etc.)
- Extract the working solution from "SOLUTION_THAT_WORKED" in the PERTS
- Remove all internal information (engineer names, case numbers, troubleshooting attempts)
- Match the tone: helpful, clear, step-by-step
- Do NOT use sections like "Problem Description", "Environment", "Root Cause" - use the format from examples!

Generate the KB article now in the EXACT format shown above:
"""
        return prompt

    def _extract_title(self, kb_content):
        """Extract title from generated KB"""
        lines = kb_content.split('\n')
        for line in lines:
            if line.strip() and not line.startswith('#'):
                # Remove markdown formatting
                title = line.replace('**', '').replace('*', '').strip()
                if len(title) > 10:
                    return title
        return "Generated KB Article"

    def generate_kb_update(self, current_kb_content, current_kb_title, issue_description, new_troubleshooting, product):
        """
        Generate an UPDATED KB by integrating engineer's proposed changes

        Args:
            current_kb_content: Current KB HTML content
            current_kb_title: Current KB title
            issue_description: What the engineer found wrong/missing
            new_troubleshooting: Engineer's proposed new steps
            product: Product name

        Returns:
            dict with 'title' and 'content' (updated KB)
        """
        import re

        # Strip HTML from current KB
        current_kb_text = re.sub(r'<[^>]+>', '', current_kb_content)
        current_kb_text = re.sub(r'\n\s*\n', '\n\n', current_kb_text)

        prompt = f"""You are updating an existing Trend Micro knowledge base article.

CURRENT KB ARTICLE:
Title: {current_kb_title}
Product: {product}

Current Content:
{current_kb_text[:3000]}

ENGINEER'S FEEDBACK:
Issue/Missing Information: {issue_description}

Proposed New Troubleshooting Steps:
{new_troubleshooting}

TASK:
Update the KB article by INTEGRATING the engineer's proposed steps into the existing content.

CRITICAL RULES:
1. DO NOT rewrite the entire KB - only add/update the relevant section
2. PRESERVE all existing content and formatting
3. ADD the new troubleshooting steps in the appropriate location:
   - If they're additional steps: add to "What should I do next?" section
   - If they're alternative solutions: add new "Alternative Solution" section
   - If they fix missing info: integrate into relevant existing section
4. MAINTAIN the same tone, style, and structure as the original
5. Keep the same title unless scope changed significantly
6. Use HTML formatting matching the original (h2, ul, li, p, strong tags)
7. Format the new steps clearly with numbered lists or bullet points

OUTPUT FORMAT:
Return the complete UPDATED KB in HTML format. Include:
- Title in <h1> tags
- Updated content with new steps integrated
- Preserve all original sections that weren't changed
"""

        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a technical writer who updates KB articles by carefully integrating new information without rewriting existing content."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2500
            )

            updated_content = response.choices[0].message.content.strip()

            # Extract title
            title_match = re.search(r'<h1>(.*?)</h1>', updated_content, re.IGNORECASE)
            if title_match:
                updated_title = title_match.group(1)
                updated_content = re.sub(r'<h1>.*?</h1>', '', updated_content, flags=re.IGNORECASE).strip()
            else:
                updated_title = current_kb_title

            return {
                'title': updated_title,
                'content': updated_content
            }

        except Exception as e:
            return {
                'title': current_kb_title,
                'content': f"""
<h2>⚠️ Error Generating Update</h2>
<p>Error: {str(e)}</p>

<h2>Engineer's Proposed Changes</h2>
<p><strong>Issue:</strong> {issue_description}</p>
<p><strong>Proposed Steps:</strong></p>
<pre>{new_troubleshooting}</pre>
"""
            }

    def save_kb_draft(self, report_id, kb_draft):
        """Save generated KB draft to database"""
        conn = get_connection()
        cursor = conn.cursor()

        # Create table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kb_drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER,
                title TEXT,
                content TEXT,
                metadata TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                reviewed_by TEXT,
                reviewed_at TEXT,
                FOREIGN KEY (report_id) REFERENCES engineer_reports(id)
            )
        ''')

        cursor.execute('''
            INSERT INTO kb_drafts (report_id, title, content, metadata, created_at, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        ''', (
            report_id,
            kb_draft['title'],
            kb_draft['content'],
            json.dumps(kb_draft['metadata']),
            datetime.now().isoformat()
        ))

        draft_id = cursor.lastrowid
        conn.commit()
        conn.close()

        print(f"   💾 KB draft saved (ID: {draft_id})")
        return draft_id

    def validate_kb_update_submission(self, kb_number, proposed_solution, engineer_notes=None):
        """
        AI validates if proposed solution already exists in the current KB

        Args:
            kb_number: KB article number (e.g., "19142")
            proposed_solution: Engineer's PERTS/proposed troubleshooting
            engineer_notes: Engineer's quick summary (optional)

        Returns:
            {
                'is_approved': bool,
                'decision': 'approved' or 'auto_rejected',
                'reasoning': str,
                'existing_content': str (if duplicate),
                'confidence': float (0-1)
            }
        """
        print(f"\n🤖 AI Validating KB Update Submission for KB-{kb_number}")

        try:
            # Fetch current KB content from database
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT title, content, product
                FROM kb_articles
                WHERE kb_number = %s
                LIMIT 1
            """, (kb_number,))

            kb_data = cursor.fetchone()
            conn.close()

            if not kb_data:
                print(f"   ⚠️ KB-{kb_number} not found in database - Auto-approving")
                return {
                    'is_approved': True,
                    'decision': 'approved',
                    'reasoning': f'KB-{kb_number} not found in local database. Submission approved for manual review.',
                    'confidence': 0.5
                }

            kb_title, kb_content, product = kb_data

            # Strip HTML tags for comparison
            import re
            kb_text = re.sub(r'<[^>]+>', '', kb_content)
            kb_text = re.sub(r'\n\s*\n', '\n\n', kb_text).strip()

            print(f"   📄 KB Title: {kb_title}")
            print(f"   📦 Product: {product}")
            print(f"   📝 KB Content Length: {len(kb_text)} chars")

            # Build AI prompt - SIMPLIFIED for reliability
            prompt = f"""You must determine: Does this KB article already tell users to perform the engineer's proposed solution?

**SINGLE DECISION RULE:**
- If KB already mentions this solution (same tool/method/action) → REJECT as duplicate
- If KB does NOT mention this solution → APPROVE as new content

**BE VERY STRICT:** Only reject if you can clearly quote where KB already covers this. When in doubt, APPROVE for human review.

**CURRENT KB ARTICLE (KB-{kb_number}):**
Title: {kb_title}
Product: {product}

Content:
{kb_text[:4000]}

---

**ENGINEER'S PROPOSED UPDATE:**
{proposed_solution}

{'**Engineer Notes:** ' + engineer_notes if engineer_notes else ''}

---

**DECISION FRAMEWORK (Use This Process):**

Step 1: Extract the SOLUTION METHOD from engineer's update
- Ignore: UI navigation paths, button names, detailed clicks
- Focus: What action/fix is being performed?

Step 2: Compare to KB using this decision tree:

┌─ Is engineer providing detailed steps for action KB already mentions?
│  (e.g., KB: "Fix time" | Engineer: "Go to Settings > Time to fix")
│  → YES: REJECT (adding detail to existing solution)
│  → NO: Continue to next check
│
┌─ Is engineer using a synonym/rephrasing of KB's solution?
│  (e.g., KB: "Update program" | Engineer: "Install latest version")
│  → YES: REJECT (same action, different words)
│  → NO: Continue to next check
│
┌─ Is engineer's method fundamentally different from KB's method?
│  (e.g., KB: "Update" | Engineer: "Reinstall fresh")
│  → YES: APPROVE (different troubleshooting approach)
│  → NO: Continue to next check
│
┌─ Do KB and engineer mention the SAME tool/file/command name?
│  (e.g., KB: "Remnant File Remover" | Engineer: "remnant file remover")
│  Extract tool names from both, compare ignoring case/articles
│  → YES: REJECT (same tool = same method)
│  → NO: Continue to next check
│
┌─ Does engineer mention specific items (files/apps) already listed in KB?
│  (e.g., KB lists ExpressVPN | Engineer: "Uninstall ExpressVPN")
│  → YES: REJECT (specific example already in KB)
│  → NO: APPROVE (new specific item not mentioned)

Step 3: Final safety check
- If still uncertain → REJECT (conservative approach)
- Only approve if clearly a NEW method not mentioned in KB

**CORE TRAINING PATTERNS (Learn these):**

Pattern 1 - SAME TOOL/FILE = DUPLICATE (REJECT):
KB: "Use Remnant File Remover tool to clean files"
Engineer: "Downloaded and ran Remnant File Remover"
Analysis: Both mention "Remnant File Remover" (same tool)
→ REJECT - Same tool, engineer just adds download detail

Pattern 2 - SAME ACTION, DIFFERENT WORDS = DUPLICATE (REJECT):
KB: "Ensure date and time are accurate"
Engineer: "Fixed by syncing Windows time settings"
Analysis: "Ensure date/time accurate" = "Sync time" (same action, different wording)
→ REJECT - Same action, engineer adds implementation detail

Pattern 3 - DIFFERENT TOOLS = NEW (APPROVE):
KB: "Remove duplicate website links in Protected Website List"
Engineer: "Removed duplicate browser extensions in Extensions Manager"
Analysis: "Website links" ≠ "Browser extensions" (different things, different locations)
→ APPROVE - Different components, not covered in KB

Pattern 4 - DIFFERENT METHODS = NEW (APPROVE):
KB: "Update Trend Micro: check for latest version"
Engineer: "Completely uninstalled and reinstalled Trend Micro"
Analysis: "Update" ≠ "Reinstall" (fundamentally different approaches)
→ APPROVE - Reinstall is different recovery method than update

Pattern 5 - SPECIFIC ITEM ALREADY LISTED = DUPLICATE (REJECT):
KB: "Uninstall conflicting VPNs: ExpressVPN, NordVPN"
Engineer: "Uninstalled ExpressVPN from Control Panel"
Analysis: KB already lists ExpressVPN
→ REJECT - KB already identifies this app, engineer adds how-to

Pattern 6 - NEW SPECIFIC ITEM = NEW (APPROVE):
KB: "Uninstall conflicting VPNs: ExpressVPN, NordVPN"
Engineer: "Uninstalled Cisco AnyConnect"
Analysis: KB doesn't mention Cisco AnyConnect
→ APPROVE - New conflicting software identified

**DETAILED EXAMPLES:**

Example 1:
KB: "Ensure App Date and Time are Accurate"
Engineer: "Fixed by syncing time in Windows Settings > Time & Language"
Core concept: Fix date/time settings
KB mentions it? YES (says "Ensure date/time accurate")
→ **REJECT** - Same concept. Engineer just provides detailed steps for what KB already says.

Example 2:
KB: "Check for and remove duplicate website links in Protected Website List"
Engineer: "Removed duplicate toolbar extension from Pay Guard browser's extension manager"
Core concept KB: Remove duplicate website links
Core concept Engineer: Remove duplicate browser extension
KB mentions it? NO (KB talks about website links, not browser extensions - different things)
→ **APPROVE** - Different concept. Browser extensions ≠ website links.

Example 3:
KB: "Uninstall conflicting VPN apps: ExpressVPN, PureVPN"
Engineer: "Uninstalled ExpressVPN from Control Panel > Programs and Features"
Core concept: Uninstall conflicting VPN apps
KB mentions it? YES (explicitly lists ExpressVPN)
→ **REJECT** - Same concept. Engineer just adds how-to steps.

Example 4 - CRITICAL DISTINCTION:
KB: "Update Trend Micro: Right-click icon → Check for Program Updates"
Engineer: "Completely uninstalled Trend Micro, then reinstalled from fresh download"
Core concept KB: Update existing installation
Core concept Engineer: Full uninstall + reinstall
KB mentions reinstalling? NO (only mentions updating)
→ **APPROVE** - Different approach. "Update" ≠ "Reinstall". These are fundamentally different troubleshooting methods.

Example 5:
KB: "Update Trend Micro by checking for updates"
Engineer: "Applied specific hotfix file: Ti_1780_win_en_uiProtectedBrowser_hfb1151.exe"
Core concept KB: Update program generally
Core concept Engineer: Apply specific named hotfix file
KB mentions this specific hotfix? Check the KB content...
If KB already mentions applying this hotfix → **REJECT**
If KB doesn't mention this specific hotfix → **APPROVE**

Example 6:
KB: "Close and reopen the VPN app"
Engineer: "Completely closed VPN app, reopened it, and clicked Connect"
Core concept: Close and reopen VPN app
KB mentions it? YES (says to close/reopen)
→ **REJECT** - Same concept. Engineer just adds "clicked Connect" detail.

Example 7:
KB: "Restart your computer"
Engineer: "Cleared Windows temporary files cache and then restarted computer"
Core concept KB: Restart computer
Core concept Engineer: Clear temp files + restart
KB mentions clearing temp files? NO (only mentions restart)
→ **APPROVE** - New concept added (clearing temp files).

Example 8 - AVOID FALSE POSITIVE:
KB: "Remove duplicate website links in Protected Website List"
Engineer: "Removed duplicate toolbar extensions in Pay Guard Extensions Manager"
Core concept KB: Remove duplicates in Protected Website List
Core concept Engineer: Remove duplicates in Extensions Manager
Are these the same location? NO (Website List ≠ Extension Manager - different settings)
→ **APPROVE** - Different location/setting, not covered in KB.

Example 9 - AVOID FALSE NEGATIVE:
KB: "Ensure subscription is active and device is registered"
Engineer: "Verified subscription status by opening app > Profile > checking expiry date"
Core concept: Check subscription status
KB mentions it? YES (says "ensure subscription is active")
→ **REJECT** - Engineer just provides detailed steps for checking subscription.

Example 10 - AVOID FALSE POSITIVE:
KB: "Update Trend Micro: Right-click icon > Check for updates"
Engineer: "Performed repair installation using Windows Programs and Features"
Core concept KB: Update program
Core concept Engineer: Repair installation
Are these the same? NO (Update ≠ Repair - different recovery methods)
→ **APPROVE** - Repair is different from Update.

Example 11 - AVOID FALSE NEGATIVE:
KB: "Disable conflicting software temporarily: ExpressVPN, NordVPN"
Engineer: "Disabled ExpressVPN by stopping the service in Task Manager"
Core concept: Disable ExpressVPN
KB mentions ExpressVPN? YES (explicitly lists it)
→ **REJECT** - KB already says to disable ExpressVPN, engineer adds how-to detail.

Example 12 - AVOID FALSE POSITIVE:
KB: "Disable conflicting software: ExpressVPN, NordVPN"
Engineer: "Uninstalled Cisco AnyConnect VPN client"
Core concept KB: Disable known VPNs (ExpressVPN, NordVPN)
Core concept Engineer: Uninstall different VPN (Cisco AnyConnect)
KB mentions Cisco AnyConnect? NO
→ **APPROVE** - New conflicting software identified, not in KB's list.

Example 13 - CRITICAL (AVOID FALSE NEGATIVE):
KB: "Download and install the Trend Micro Remnant File Remover Tool to clean leftover files"
Engineer: "Used remnant file remover to clean installation remnants"
Tool in KB: "Trend Micro Remnant File Remover Tool"
Tool in Engineer: "remnant file remover"
Same tool? YES (same tool, slightly different wording)
→ **REJECT** - Both using the SAME TOOL. Engineer is not introducing new method.

Example 14 - CRITICAL (AVOID FALSE NEGATIVE):
KB: "Apply hotfix: Ti_1780_win_en_uiProtectedBrowser_hfb1151.exe"
Engineer: "Downloaded and installed hotfix Ti_1780_win_en_uiProtectedBrowser_hfb1151.exe"
File in KB: Ti_1780_win_en_uiProtectedBrowser_hfb1151.exe
File in Engineer: Ti_1780_win_en_uiProtectedBrowser_hfb1151.exe
Same file? YES (exact same filename)
→ **REJECT** - Both using the SAME HOTFIX FILE. Not a new solution.

Example 15 - TOOL NAME MATCHING:
KB: "Run System File Checker: Open CMD and type 'sfc /scannow'"
Engineer: "Fixed by running sfc /scannow command in Command Prompt"
Command in KB: sfc /scannow
Command in Engineer: sfc /scannow
Same command? YES
→ **REJECT** - Same command, engineer just rewords the KB's existing instruction.

**CRITICAL DISTINCTIONS (Common Edge Cases):**

DIFFERENT METHODS (APPROVE):
- "Update program" ≠ "Reinstall program" ≠ "Repair program" (all different approaches)
- "Restart computer" ≠ "Restart in Safe Mode" (different troubleshooting depth)
- "Clear browser cache" ≠ "Clear app cache" (different locations)
- "Disable Windows Defender" ≠ "Add exclusion in Windows Defender" (different actions)
- "Run program as admin" ≠ "Run program normally" (different execution method)
- "Edit registry key X" ≠ "Edit registry key Y" (different keys)
- "Use Tool A" ≠ "Use Tool B" (different tools)
- "Repair installation" ≠ "Clean reinstall" (different repair methods)
- "Apply hotfix ABC.exe" ≠ "Apply hotfix XYZ.exe" (different patch files)

SAME METHOD (REJECT):
- "Fix date/time" = "Sync time settings" = "Correct clock" (same thing, different words)
- "Update to latest" = "Check for updates and install" (same method, more detail)
- "Remove conflicting app" = "Uninstall ExpressVPN" when KB lists ExpressVPN (KB already mentions it)
- "Restart app" = "Close app completely and reopen" (same action, more words)
- "Enable feature X" = "Turn on feature X" = "Activate feature X" (same action, synonyms)
- "Use Remnant File Remover" = "Download and run Remnant File Remover Tool" (SAME TOOL, different wording)
- "Apply hotfix ABC.exe" = "Install hotfix ABC.exe" when KB mentions ABC.exe (SAME FILE)
- "Run Diagnostic Tool" = "Use Trend Micro Diagnostic Tool" when KB mentions it (SAME TOOL)

**CRITICAL RULE FOR TOOL/FILE NAMES:**
If both KB and engineer mention the SAME tool name, software name, or file name → REJECT
Examples:
- KB: "Use Remnant File Remover" | Engineer: "Download Remnant File Remover" → SAME TOOL (REJECT)
- KB: "Apply hotfix Ti_1780.exe" | Engineer: "Install hotfix Ti_1780.exe" → SAME FILE (REJECT)
- KB: "Run System File Checker (sfc /scannow)" | Engineer: "Use sfc /scannow command" → SAME COMMAND (REJECT)

TRICKY CASES:
- KB: "Apply latest patches" | Engineer: "Applied hotfix ABC.exe" → Check if KB mentions ABC.exe
  - If KB mentions ABC.exe → REJECT (same hotfix)
  - If KB doesn't mention ABC.exe → APPROVE (specific new hotfix)
- KB: "Uninstall conflicting software" | Engineer: "Uninstalled Zoom" → Check if KB lists Zoom
  - If KB lists Zoom → REJECT (already mentioned)
  - If KB doesn't list Zoom → APPROVE (new conflicting app identified)
- KB: "Clear cache" | Engineer: "Clear cache then restart" → Partial overlap
  - If KB already mentions restart → REJECT (all steps covered)
  - If KB doesn't mention restart → APPROVE (adds new step)

**KEY PRINCIPLE:**
More detail ≠ New content
Different wording ≠ New content
Different CORE CONCEPT = New content

**YOUR ANALYSIS:**
1. Identify the main solution concept(s) in engineer's update
2. For each concept, ask: "Does KB already tell users to do this?"
3. If ALL concepts are already in KB → REJECT
4. If ANY concept is NEW (not in KB) → APPROVE

**YOUR ANALYSIS CHECKLIST (Follow this):**

Step 1: Extract core solution from engineer
- Ignore: UI paths, button clicks, detailed navigation
- Extract: Tool name, command, action being performed

Step 2: Search KB for mentions of this solution
- Look for: Same tool name, same command, same action
- Use: Pattern matching from training above

Step 3: Make decision using these rules:
✓ REJECT if: Same tool mentioned in both (e.g., both say "Remnant File Remover")
✓ REJECT if: Same action, different wording (e.g., "Fix time" vs "Sync time")
✓ REJECT if: Specific item already in KB's list (e.g., KB lists "ExpressVPN", engineer says "Uninstall ExpressVPN")
✓ APPROVE if: Different tool/method entirely (e.g., "Update" vs "Reinstall")
✓ APPROVE if: New item not in KB's list (e.g., KB lists "ExpressVPN", engineer mentions "Cisco AnyConnect")

Step 4: Confidence check
- Only use confidence 0.93-0.97 if absolutely certain
- If confidence < 0.93 on REJECT → System will auto-approve for human review
- When uncertain → Use low confidence (system will approve it)

**OUTPUT FORMAT (JSON only):**
{{
    "decision": "approved" OR "auto_rejected",
    "reasoning": "Step-by-step: Engineer's solution is [X]. KB mentions [Y or 'nothing similar']. Pattern: [Same tool/Different method/etc]. Therefore: [duplicate/new].",
    "existing_content": "Exact KB quote showing duplicate if rejecting, or null if approving",
    "confidence": 0.93 to 0.97 (use 0.93 if somewhat certain, 0.97 if absolutely certain)
}}

Respond with ONLY valid JSON."""

            # Call Azure OpenAI
            print("   🔄 Calling Azure OpenAI for validation...")
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a KB duplicate detector. Your job: Determine if KB already tells users to do what engineer proposes. RULES: Same tool/file = REJECT. Same action in different words = REJECT. Different tool/method = APPROVE. Item already in KB list = REJECT. New item not in list = APPROVE. CRITICAL: Only use confidence 0.93+ on rejections. If unsure, use low confidence (system will approve for human review). Output valid JSON only with exact format specified."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.0,  # Zero for maximum determinism and consistency
                max_tokens=600  # Reduced - simpler reasoning now
            )

            ai_response = response.choices[0].message.content.strip()
            print(f"   📥 AI Response: {ai_response[:200]}...")

            # Parse JSON response
            try:
                # Extract JSON if wrapped in markdown code blocks
                if '```json' in ai_response:
                    ai_response = ai_response.split('```json')[1].split('```')[0].strip()
                elif '```' in ai_response:
                    ai_response = ai_response.split('```')[1].split('```')[0].strip()

                result = json.loads(ai_response)

                # Validate required fields
                if 'decision' not in result:
                    raise ValueError("Missing 'decision' field in AI response")

                # Default values for optional fields
                result.setdefault('reasoning', 'No reasoning provided')
                result.setdefault('existing_content', None)
                result.setdefault('confidence', 0.7)

                # STRICT confidence threshold: Only auto-reject if VERY confident
                confidence_threshold = 0.93  # Increased from 0.80 to 0.93 - be very conservative
                if result['decision'] == 'auto_rejected' and result['confidence'] < confidence_threshold:
                    print(f"   ⚠️ Low confidence ({result['confidence']:.0%}) on rejection - defaulting to APPROVE for manual review")
                    result['decision'] = 'approved'
                    result['reasoning'] = f"AI uncertainty: {result['reasoning']} (Confidence {result['confidence']:.0%} below {confidence_threshold:.0%} threshold - requires human review)"
                    result['confidence'] = 0.5

                # Secondary validation: Detect obvious false positives (wrongly rejecting valid new methods)
                proposed_lower = proposed_solution.lower()
                kb_lower = kb_text.lower()

                # Keywords indicating genuinely different methods that should be approved
                different_method_indicators = [
                    ('reinstall', 'update', 'Reinstall is different from update'),
                    ('repair', 'update', 'Repair is different from update'),
                    ('safe mode', 'normal mode', 'Safe mode is different troubleshooting'),
                    ('registry', 'settings', 'Registry edit is different from GUI settings'),
                    ('clean install', 'update', 'Clean install is different from update'),
                    ('third-party tool', 'built-in', 'Third-party tool is different approach')
                ]

                if result['decision'] == 'auto_rejected':
                    for new_keyword, kb_keyword, reason in different_method_indicators:
                        if new_keyword in proposed_lower and kb_keyword in kb_lower and new_keyword not in kb_lower:
                            print(f"   🔍 Secondary validation: Detected potential false positive - {reason}")
                            print(f"   ✓ Overriding AI decision: APPROVED (engineer uses '{new_keyword}', KB only mentions '{kb_keyword}')")
                            result['decision'] = 'approved'
                            result['is_approved'] = True
                            result['reasoning'] = f"Override: {reason}. Engineer proposes '{new_keyword}' which is not mentioned in KB. Original AI reasoning: {result['reasoning']}"
                            result['confidence'] = 0.85
                            break

                # Tertiary validation: Detect false negatives (wrongly approving when same tool/file mentioned)
                if result['decision'] == 'approved':
                    # Extract key technical terms from engineer's solution
                    import re

                    # Find specific tool/file names (look for capitalized multi-word terms, .exe files, version numbers)
                    engineer_tools = set()
                    kb_tools = set()

                    # Pattern 1: .exe files
                    exe_pattern = r'\b[\w_]+\.exe\b'
                    engineer_tools.update(re.findall(exe_pattern, proposed_lower))
                    kb_tools.update(re.findall(exe_pattern, kb_lower))

                    # Pattern 2: Common tool phrases
                    tool_phrases = [
                        'remnant file remover', 'diagnostic tool', 'uninstaller', 'cleanup tool',
                        'system file checker', 'sfc /scannow', 'dism', 'chkdsk', 'disk cleanup',
                        'hotfix', 'patch', 'update tool', 'repair tool', 'registry cleaner'
                    ]

                    for phrase in tool_phrases:
                        if phrase in proposed_lower:
                            engineer_tools.add(phrase)
                        if phrase in kb_lower:
                            kb_tools.add(phrase)

                    # Check for overlap in tool names
                    common_tool_mentions = engineer_tools & kb_tools

                    if common_tool_mentions:
                        tool_list = ', '.join(common_tool_mentions)
                        print(f"   🔍 Tertiary validation: Both KB and engineer mention same tool(s): {tool_list}")
                        print(f"   ✗ Overriding AI decision: REJECTED (same tool = same method)")
                        result['decision'] = 'auto_rejected'
                        result['is_approved'] = False
                        result['reasoning'] = f"Override: Both KB and engineer use the same tool/file ({tool_list}). This is not a new method. Engineer is just providing more detail for existing KB solution."
                        result['confidence'] = 0.94
                        result['existing_content'] = f"KB already mentions: {tool_list}"

                # Add is_approved field
                result['is_approved'] = (result['decision'] == 'approved')

                decision_emoji = "✅" if result['is_approved'] else "❌"
                print(f"   {decision_emoji} Decision: {result['decision'].upper()}")
                print(f"   💭 Reasoning: {result['reasoning']}")
                print(f"   📊 Confidence: {result['confidence']:.0%}")

                # Final summary for debugging
                print(f"\n   📋 VALIDATION SUMMARY:")
                print(f"      • KB Article: KB-{kb_number} ({kb_title})")
                print(f"      • Final Decision: {result['decision'].upper()}")
                print(f"      • Confidence: {result['confidence']:.0%}")
                print(f"      • Will appear in dashboard: {'NO (Blocked)' if not result['is_approved'] else 'YES (Approved)'}")
                if not result['is_approved']:
                    print(f"      • Email sent: Auto-rejection notification")
                else:
                    print(f"      • Email sent: Submission confirmation")

                return result

            except json.JSONDecodeError as e:
                print(f"   ⚠️ JSON Parse Error: {e}")
                # Fallback: Auto-approve if we can't parse AI response
                return {
                    'is_approved': True,
                    'decision': 'approved',
                    'reasoning': f'AI validation failed (JSON parse error). Submission approved for manual review.',
                    'confidence': 0.3
                }

        except Exception as e:
            print(f"   ❌ Validation Error: {str(e)}")
            # Fallback: Auto-approve on error (don't block submissions)
            return {
                'is_approved': True,
                'decision': 'approved',
                'reasoning': f'AI validation error: {str(e)}. Submission approved for manual review.',
                'confidence': 0.3
            }


def test_generator(report_id=None):
    """Test the KB generator"""
    try:
        generator = KBGenerator()

        if not report_id:
            # Get the latest "no_kb_exists" report
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM engineer_reports
                WHERE report_type = 'no_kb_exists'
                ORDER BY id DESC LIMIT 1
            ''')
            row = cursor.fetchone()
            conn.close()

            if not row:
                print("No 'no_kb_exists' reports found to test")
                return

            report_id = row[0]

        result = generator.generate_kb_draft(report_id)

        if result.get('success'):
            print("\n" + "="*70)
            print("GENERATED KB DRAFT:")
            print("="*70)
            print(result['content'])
            print("="*70)
            print(f"Tokens used: {result['tokens_used']}")

            # Save to database
            draft_id = generator.save_kb_draft(report_id, result)
            print(f"\n✅ Draft saved with ID: {draft_id}")

        else:
            print(f"\n❌ Generation failed: {result.get('error')}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have:")
        print("1. Created .env file with Azure OpenAI credentials")
        print("2. Installed required packages: pip install openai python-dotenv")


def parse_solution_from_perts(perts_text):
    """
    Extract SOLUTION_THAT_WORKED section from PERTS
    Returns just the solution text without the header
    """
    solution_section = ""
    lines = perts_text.split('\n')
    capturing = False

    for line in lines:
        line_upper = line.strip().upper()

        if 'SOLUTION_THAT_WORKED' in line_upper or 'SOLUTION THAT WORKED' in line_upper:
            capturing = True
            continue
        elif line_upper and line_upper.replace('_', '').replace(' ', '').isalpha() and len(line_upper) > 8:
            # Hit another PERTS section header
            if capturing:
                break
        elif capturing and line.strip():
            if line.strip().lower() not in ['n/a', 'na', 'none']:
                solution_section += line + "\n"

    return solution_section.strip()


def format_missing_step_manually(solution_text, issue_description):
    """
    Format the missing step WITHOUT using AI - just clean formatting
    This prevents AI from regenerating the entire KB
    """
    if not solution_text:
        return None

    # Clean up the solution text
    lines = solution_text.strip().split('\n')
    formatted_lines = []

    for line in lines:
        line = line.strip()
        if line:
            # If it's not already bulleted/numbered, add a bullet
            if not line[0].isdigit() and not line.startswith('•') and not line.startswith('-'):
                formatted_lines.append(f"• {line}")
            else:
                formatted_lines.append(line)

    formatted_solution = '\n'.join(formatted_lines)

    # Create the output
    output = f"""---
📍 **WHERE TO INSERT THIS:**

Add as a new troubleshooting section at the end of existing steps (before contacting support).

Suggested section title: **"If the issue persists"** or **"Additional Troubleshooting Step"**

---

🆕 **NEW STEP TO ADD TO THE KB:**

{formatted_solution}

---

💡 **WHY THIS IS NEEDED:**

{issue_description}

---

⚠️ **IMPORTANT:** This is ONLY the new content to ADD to the existing KB article. Do NOT remove or replace any existing steps. Simply insert this as an additional troubleshooting option.
"""
    return output, formatted_solution


def apply_incremental_update_to_kb(current_kb_content, new_step_content, update_type='kb_missing_steps'):
    """
    Apply the incremental update to the actual KB content
    Scans for redundancies and inserts the new step intelligently
    Returns the complete updated KB with the changes applied

    Args:
        current_kb_content: Current KB HTML/text content
        new_step_content: The new step/change to add (already formatted)
        update_type: Type of update

    Returns:
        Complete updated KB content
    """
    import re

    # Scan for redundancies - check if the new step content already exists
    content_lower = current_kb_content.lower()
    new_step_lower = new_step_content.lower()

    # Extract key phrases from new step (first 50 chars of meaningful text)
    key_phrases = re.findall(r'\b\w{4,}\b', new_step_lower)[:10]  # Get first 10 meaningful words

    # Check if the KB already contains similar content
    redundancy_found = False
    for phrase in key_phrases:
        if len(phrase) > 6 and phrase in content_lower:
            # Found potential redundancy, but don't block - just note it
            redundancy_found = True
            break

    # Keep HTML structure for proper display
    kb_html = current_kb_content

    # Strip HTML tags for plain text version to find insertion point
    kb_text = re.sub(r'<[^>]+>', '', kb_html)
    kb_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', kb_text).strip()

    if update_type == 'kb_missing_steps':
        # Format the new step as plain text to match KB style
        import re

        # Extract title if present (line starting with **)
        title_match = re.search(r'\*\*(.*?)\*\*', new_step_content)
        step_title = title_match.group(1) if title_match else "Additional Troubleshooting"

        # Extract and renumber steps consistently
        step_lines = []
        step_num = 1

        for line in new_step_content.split('\n'):
            line = line.strip()
            if not line or line.startswith('**'):
                continue

            # Match numbered steps like "1. Do something" or unnumbered action steps
            if re.match(r'^\d+\.', line):
                # Remove existing number and renumber
                clean_line = re.sub(r'^\d+\.\s*', '', line)
                step_lines.append(f"{step_num}. {clean_line}")
                step_num += 1
            elif line and not title_match.group(0) in line:
                # Add number to unnumbered action line
                step_lines.append(f"{step_num}. {line}")
                step_num += 1

        # Build plain text format with proper line breaks
        steps_text = '\n'.join(step_lines)
        new_step_text = f"\n\n{step_title}\n{steps_text}\n"

        # Ensure KB content ends properly
        kb_html = kb_html.rstrip() + '\n'

        # Try to find a good insertion point
        # Look for HTML end tags
        html_match = re.search(r'(</body>|</html>)', kb_html, re.IGNORECASE)

        # Look for contact support or feedback
        contact_match = re.search(r'(contact.*?support|Was this.*?helpful|Did this.*?solve)', kb_html, re.IGNORECASE)

        insertion_point = None

        # Priority: Insert before HTML end tags
        if html_match:
            insertion_point = html_match.start()
        # Then before contact/feedback
        elif contact_match:
            insertion_point = contact_match.start()

        # If no good insertion point found, append at the end
        if insertion_point is None:
            # Append with proper spacing
            updated_kb = kb_html.rstrip() + '\n' + new_step_text
        else:
            # Insert at the found point with proper spacing
            before_part = kb_html[:insertion_point].rstrip()
            after_part = kb_html[insertion_point:].lstrip()
            updated_kb = before_part + '\n' + new_step_text + '\n' + after_part
    else:
        # For outdated, append the change
        new_step_text = f"Updated Section\n{new_step_content}\n"
        updated_kb = kb_html + '\n\n' + new_step_text

    return updated_kb


def generate_incremental_kb_update(current_kb_content, current_kb_title, issue_description, new_troubleshooting, update_type, product, manager_notes=None, engineer_notes=None):
    """
    Generate INCREMENTAL update instructions (not full KB rewrite)

    For kb_missing_steps: Generate only the steps to ADD
    For kb_outdated: Generate only the specific CHANGES to make

    Args:
        current_kb_content: Current KB HTML content
        current_kb_title: Current KB title
        issue_description: What the engineer found wrong/missing
        new_troubleshooting: Engineer's proposed steps (PERTS format)
        update_type: Either 'kb_missing_steps' or 'kb_outdated'
        product: Product name
        manager_notes: Optional manager feedback/notes for additional context
        engineer_notes: Optional engineer's quick summary of the fix

    Returns:
        dict with 'title' and 'content' (incremental update instructions)
    """
    import re

    # Parse PERTS to extract SOLUTION_THAT_WORKED section
    solution_section = parse_solution_from_perts(new_troubleshooting)

    # If no SOLUTION_THAT_WORKED found, try to extract from the entire PERTS
    if not solution_section or len(solution_section) < 20:
        solution_section = new_troubleshooting.strip()

    # FOR MISSING STEPS: Use AI to convert engineer notes to customer-facing step
    if update_type == 'kb_missing_steps':
        # Use AI to convert engineer's notes into a proper customer-facing step
        try:
            generator = KBGenerator()

            # Build context string with optional notes
            context_parts = [
                f"Issue: {issue_description}",
                f"Product: {product}"
            ]
            if engineer_notes:
                context_parts.append(f"Engineer's Quick Summary: {engineer_notes}")
            if manager_notes:
                context_parts.append(f"Manager Notes (for context only): {manager_notes}")

            context_str = "\n".join(context_parts)

            prompt = f"""You are converting an engineer's troubleshooting notes into a customer-facing KB step.

ENGINEER'S NOTES (from SOLUTION_THAT_WORKED):
{solution_section}

CONTEXT:
{context_str}

YOUR TASK:
Convert the engineer's notes above into a clear, customer-facing troubleshooting step. Follow Trend Micro KB style:

OUTPUT ONLY THIS:

**[Clear step title describing what to do]**

1. [First action - clear, simple instruction]
2. [Second action - clear, simple instruction]
3. [Continue with numbered steps]
4. [Final step]
5. Try accessing the website again.

RULES:
- Convert engineer shorthand to full sentences (e.g., "-opened edge" → "Open Microsoft Edge")
- Remove internal notes (e.g., "-entitlement checked")
- Write in active voice, customer-friendly language
- Number the steps clearly
- Keep it simple and actionable
- Maximum 5-7 steps

Output only the formatted step - no explanations:
"""

            response = generator.client.chat.completions.create(
                model=generator.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You convert engineer notes into customer-facing KB steps. Output only the formatted step, nothing else."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=500
            )

            formatted_step = response.choices[0].message.content.strip()

            # Apply the update to the actual KB content
            updated_kb_content = apply_incremental_update_to_kb(
                current_kb_content,
                formatted_step,
                update_type='kb_missing_steps'
            )

            return {
                'title': f"New Step to ADD to {current_kb_title}",
                'content': formatted_step,
                'updated_kb': updated_kb_content
            }

        except Exception as e:
            # Fallback to manual if AI fails
            result = format_missing_step_manually(solution_section, issue_description)
            if result:
                manual_output, formatted_step = result
                updated_kb_content = apply_incremental_update_to_kb(
                    current_kb_content,
                    formatted_step,
                    update_type='kb_missing_steps'
                )
                return {
                    'title': f"New Step to ADD to {current_kb_title}",
                    'content': manual_output,
                    'updated_kb': updated_kb_content
                }
            else:
                return {
                    'title': f"Update for {current_kb_title}",
                    'content': f"Error: {str(e)}\n\nRaw solution:\n{solution_section}",
                    'updated_kb': current_kb_content
                }

    # FOR OUTDATED: Still use AI but with very restrictive prompt
    # Strip HTML from current KB (for context, but minimal)
    current_kb_text = re.sub(r'<[^>]+>', '', current_kb_content)
    current_kb_text = re.sub(r'\n\s*\n', '\n\n', current_kb_text)

    # Get section headers from KB for context
    kb_sections = re.findall(r'([A-Z][^?\n]*\?)', current_kb_text[:1000])  # Extract question headers
    kb_context = "KB has sections like: " + ", ".join(kb_sections[:3]) if kb_sections else "Standard KB format"

    # Build prompt for OUTDATED type only (kb_missing_steps is handled manually above)
    if update_type == 'kb_outdated':
        # Add engineer notes and manager notes to context if available
        additional_context_parts = []
        if engineer_notes:
            additional_context_parts.append(f"💡 ENGINEER'S QUICK SUMMARY:\n{engineer_notes}")
        if manager_notes:
            additional_context_parts.append(f"📝 MANAGER NOTES (for context only):\n{manager_notes}")

        additional_context = "\n\n" + "\n\n".join(additional_context_parts) if additional_context_parts else ""

        prompt = f"""You are formatting a CORRECTION for outdated text in an existing Trend Micro KB article.

📄 KB ARTICLE CONTEXT:
Title: {current_kb_title}
Product: {product}
{kb_context}

🔍 CORRECTED SOLUTION (from engineer's field report):
{solution_section}

Issue Found: {issue_description}{additional_context}

YOUR ONLY TASK:
Based on the engineer's corrected solution above, identify what specific text needs updating in the KB. Output ONLY the change instructions - DO NOT regenerate the entire KB.

OUTPUT FORMAT:

---
📍 **What section to update:**
[e.g., "In troubleshooting steps section" or "Step 2 of existing solution"]

❌ **Text to find and replace:**
[Describe what outdated text to look for, based on the issue]

✅ **Replace with:**
[Provide the corrected version from engineer's solution above]

💡 **Reason for change:**
{issue_description}

---

CRITICAL RULES:
✅ Show ONLY what needs to change
✅ Be specific about the correction
✅ Make the replacement text clear and detailed
❌ DO NOT regenerate the entire KB
❌ DO NOT include unchanged steps
❌ DO NOT rewrite sections that are fine

Output the change instruction now:
"""

    try:
        generator = KBGenerator()
        response = generator.client.chat.completions.create(
            model=generator.deployment,
            messages=[
                {
                    "role": "system",
                    "content": "You format specific incremental updates for KB articles. You output ONLY the new content to add or the specific change to make. You NEVER regenerate entire articles. Focus on the delta/change only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.15,  # Low for consistency
            max_tokens=1500  # Allow detailed steps but not full KB regeneration
        )

        update_instructions = response.choices[0].message.content.strip()

        # Validation: Check if output looks like it regenerated the entire KB
        word_count = len(update_instructions.split())

        # Check for signs of full KB regeneration:
        # 1. Has "Why did this happen?" AND "What should I do next?" (full KB structure)
        # 2. Excessively long (> 600 words for a single step is suspicious)
        has_full_kb_structure = (
            ('why did this happen' in update_instructions.lower() or 'why did it happen' in update_instructions.lower()) and
            ('what should i do' in update_instructions.lower() or 'how do i fix' in update_instructions.lower())
        )

        if has_full_kb_structure or word_count > 600:
            # Output looks like it regenerated the KB
            update_instructions = f"""⚠️ **AI regenerated the entire KB instead of just the incremental change** (Output: {word_count} words)

Please review the engineer's solution below and manually create the update instruction.

**What the engineer found:**
{issue_description}

**Engineer's Solution (extract from PERTS):**
{solution_section if solution_section else new_troubleshooting}

---
💡 **What to do:**
For "Missing Steps": Format the solution above as a new step/section to ADD to the existing KB
For "Outdated": Identify what specific text in the KB needs to be replaced with the solution above

Do NOT recreate the entire KB - just show what to add or change.
"""

        # Create title based on update type
        if update_type == 'kb_missing_steps':
            title = f"New Step to ADD to KB-{current_kb_title}"
        else:
            title = f"Text Change for KB-{current_kb_title}"

        return {
            'title': title,
            'content': update_instructions
        }

    except Exception as e:
        # Fallback: show engineer's PERTS if AI fails
        return {
            'title': f"Update Instructions for {current_kb_title}",
            'content': f"""⚠️ AI generation failed: {str(e)}

**Manual Review Required**

**Issue Identified:**
{issue_description}

**Engineer's Proposed Changes (PERTS):**
{new_troubleshooting}

**Action Required:**
Please manually review the engineer's PERTS and apply the necessary updates to the KB article.
"""
        }


def generate_kb_update(current_kb_content, current_kb_title, issue_description, new_troubleshooting, product):
    """
    Wrapper function for easy import
    """
    try:
        generator = KBGenerator()
        return generator.generate_kb_update(
            current_kb_content,
            current_kb_title,
            issue_description,
            new_troubleshooting,
            product
        )
    except Exception as e:
        return {
            'title': current_kb_title,
            'content': f"""
<h2>⚠️ Error Generating Update</h2>
<p>Error: {str(e)}</p>
<p>Please check Azure OpenAI configuration.</p>

<h2>Engineer's Proposed Changes</h2>
<p><strong>Issue:</strong> {issue_description}</p>
<p><strong>Proposed Steps:</strong></p>
<pre>{new_troubleshooting}</pre>
"""
        }


def improve_engineer_submission(product, issue_description, troubleshooting_steps, manager_feedback=None, improvement_type="enhance"):
    """
    AI assistant for revision portal - improves engineer's submission based on feedback

    Args:
        product: Product name
        issue_description: Current issue description
        troubleshooting_steps: Current PERTS/troubleshooting content
        manager_feedback: Optional manager feedback to address
        improvement_type: "enhance", "rewrite_issue", "generate_missing", or "improve_clarity"

    Returns:
        str: Improved content
    """
    try:
        generator = KBGenerator()

        if improvement_type == "enhance":
            prompt = f"""You are helping an engineer improve their KB submission based on manager feedback.

PRODUCT: {product}

CURRENT ISSUE DESCRIPTION:
{issue_description}

CURRENT TROUBLESHOOTING STEPS:
{troubleshooting_steps}

{"MANAGER'S FEEDBACK:\n" + manager_feedback if manager_feedback else ""}

YOUR TASK:
Enhance the troubleshooting steps with more detail. Add:
- Specific error messages or symptoms
- Root cause explanation
- Clear step-by-step instructions
- Expected results for each step
- Any relevant technical details

Output the IMPROVED TROUBLESHOOTING STEPS in clear, professional format:"""

        elif improvement_type == "rewrite_issue":
            prompt = f"""You are helping an engineer rewrite their issue description for a KB submission.

PRODUCT: {product}

CURRENT ISSUE DESCRIPTION:
{issue_description}

{"MANAGER'S FEEDBACK:\n" + manager_feedback if manager_feedback else ""}

YOUR TASK:
Rewrite the issue description to be:
- Clear and concise
- Focused on the problem/symptom
- Professional and customer-facing
- Include key details (error codes, symptoms, affected features)

Output only the IMPROVED ISSUE DESCRIPTION:"""

        elif improvement_type == "generate_missing":
            prompt = f"""You are helping an engineer complete missing troubleshooting steps.

PRODUCT: {product}

ISSUE: {issue_description}

CURRENT STEPS (INCOMPLETE):
{troubleshooting_steps}

{"MANAGER'S FEEDBACK:\n" + manager_feedback if manager_feedback else ""}

YOUR TASK:
Generate the MISSING steps that should be added. Fill in gaps like:
- Prerequisites or environment checks
- Verification steps
- Alternative solutions
- Rollback procedures if needed

Output the MISSING STEPS to add:"""

        else:  # improve_clarity
            prompt = f"""You are helping an engineer improve the clarity and structure of their KB submission.

PRODUCT: {product}

ISSUE: {issue_description}

CURRENT STEPS:
{troubleshooting_steps}

{"MANAGER'S FEEDBACK:\n" + manager_feedback if manager_feedback else ""}

YOUR TASK:
Improve clarity and structure:
- Better section organization
- Clearer step numbering
- Improved wording and grammar
- Consistent formatting
- Remove ambiguity

Output the IMPROVED, WELL-STRUCTURED CONTENT:"""

        response = generator.client.chat.completions.create(
            model=generator.deployment,
            messages=[
                {"role": "system", "content": "You are a technical writing assistant helping engineers create clear, professional KB articles. Output clean, formatted content without preamble."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"❌ AI Generation Error: {str(e)}\n\nPlease try again or proceed with manual edits."


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        report_id = int(sys.argv[1])
        test_generator(report_id)
    else:
        print("Testing with latest 'no_kb_exists' report...")
        test_generator()
