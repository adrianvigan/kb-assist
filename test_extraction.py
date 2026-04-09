"""Test extraction logic for revision notes"""

# Simulate the notes field from database
notes = """[REVISION OF REQ-000083]
test

[ORIGINAL FEEDBACK]
GENERAL FEEDBACK:
test"""

print("Original notes field:")
print(repr(notes))
print("\n" + "="*50 + "\n")

# Test extraction logic
feedback_text = None

if '[REVISION OF' in notes and '[ORIGINAL FEEDBACK]' in notes:
    print("✅ Condition matched: Both markers found")
    feedback_text = notes.split('[ORIGINAL FEEDBACK]', 1)[1].strip()
    print(f"\nExtracted feedback_text:")
    print(repr(feedback_text))
    print("\nActual display:")
    print(feedback_text)
elif 'GENERAL FEEDBACK:' in notes or 'TECHNICAL ISSUES:' in notes:
    print("⚠️ Using fallback condition")
    feedback_text = notes

print("\n" + "="*50)
print(f"\nWill display feedback? {feedback_text and ('GENERAL FEEDBACK:' in feedback_text or 'TECHNICAL ISSUES:' in feedback_text)}")
