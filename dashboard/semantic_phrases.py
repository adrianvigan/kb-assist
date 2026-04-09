"""
Semantic Phrase Matching
Maps common problem phrases to their semantic equivalents
"""

# Problem phrase mappings
# Key: canonical phrase, Value: list of equivalent phrases
PROBLEM_PHRASES = {
    # Connection/Disconnection Issues
    'keeps reconnecting': [
        'auto-reconnect', 'autoreconnect', 'reconnects automatically', 'reconnects immediately',
        'connects back', 'connecting back', 'auto reconnect', 'automatically reconnects',
        'reconnect automatically', 'keeps connecting back', 'won\'t stay disconnected',
        'auto reconnect issues', 'autoreconnect issues'
    ],
    'won\'t disconnect': [
        'can\'t disconnect', 'unable to disconnect', 'disconnect fails',
        'won\'t turn off', 'can\'t turn off', 'cannot disconnect',
        'disconnect not working', 'disconnect doesn\'t work'
    ],
    'connection drops': [
        'keeps disconnecting', 'disconnects frequently', 'connection lost',
        'loses connection', 'unstable connection', 'connection interrupted'
    ],
    'can\'t connect': [
        'won\'t connect', 'unable to connect', 'connection failed',
        'cannot connect', 'connection error', 'fails to connect'
    ],

    # Performance Issues
    'slow performance': [
        'running slow', 'sluggish', 'takes forever', 'very slow',
        'performance issues', 'slow response', 'lagging', 'freezing'
    ],
    'high cpu usage': [
        'high cpu', 'cpu spike', 'cpu 100%', 'maxing out cpu',
        'cpu usage high', 'using too much cpu'
    ],
    'memory leak': [
        'high memory', 'memory usage high', 'ram usage high',
        'out of memory', 'using too much memory'
    ],

    # Installation Issues
    'won\'t install': [
        'installation fails', 'can\'t install', 'setup error',
        'install failed', 'installation error', 'unable to install',
        'install not working', 'setup fails'
    ],
    'installation stuck': [
        'install hangs', 'setup hangs', 'install freezes',
        'installation hanging', 'stuck at installing', 'stuck during install'
    ],
    'won\'t uninstall': [
        'can\'t uninstall', 'uninstall fails', 'unable to uninstall',
        'uninstall error', 'removal fails', 'can\'t remove'
    ],

    # Activation/License Issues
    'activation failed': [
        'can\'t activate', 'activation error', 'unable to activate',
        'activation not working', 'won\'t activate'
    ],
    'license invalid': [
        'license error', 'license expired', 'invalid license',
        'license not valid', 'license rejected'
    ],

    # Scanning Issues
    'scan won\'t start': [
        'can\'t scan', 'scan fails', 'scan not working',
        'unable to scan', 'scan doesn\'t start'
    ],
    'scan stuck': [
        'scan hangs', 'scan freezes', 'scan not progressing',
        'scan hanging', 'stuck at scanning'
    ],

    # Update Issues
    'won\'t update': [
        'can\'t update', 'update fails', 'update error',
        'unable to update', 'update not working'
    ],
    'update stuck': [
        'update hangs', 'update freezes', 'stuck at updating',
        'update hanging', 'update not progressing'
    ],

    # Error Messages
    'error message': [
        'getting error', 'shows error', 'error appears',
        'error displayed', 'receiving error'
    ],

    # VPN Specific
    'vpn always on': [
        'auto vpn', 'automatic vpn', 'vpn auto-connect',
        'vpn automatically connects', 'vpn turns on automatically'
    ],
    'vpn won\'t turn off': [
        'vpn stays on', 'can\'t turn off vpn', 'vpn won\'t disable',
        'unable to disable vpn', 'vpn keeps running'
    ],

    # Password Manager
    'password not saved': [
        'can\'t save password', 'password won\'t save', 'password not saving',
        'unable to save password', 'save password fails'
    ],
    'autofill not working': [
        'autofill fails', 'auto-fill not working', 'won\'t autofill',
        'autofill doesn\'t work', 'can\'t autofill'
    ],

    # Security/Threats
    'threat detected': [
        'virus detected', 'malware detected', 'threat found',
        'virus found', 'infected', 'malware found'
    ],
    'false positive': [
        'blocked incorrectly', 'flagged incorrectly', 'wrong detection',
        'incorrectly detected', 'safe file blocked'
    ],
}


def normalize_phrase(text):
    """Normalize text for phrase matching"""
    if not text:
        return ""

    # Convert to lowercase
    text = text.lower()

    # Remove extra whitespace
    import re
    text = re.sub(r'\s+', ' ', text)

    # Remove special characters except apostrophes
    text = re.sub(r'[^\w\s\']', '', text)

    return text.strip()


def find_matching_phrases(text):
    """
    Find semantic phrases in text

    Args:
        text: Text to search for phrases

    Returns:
        List of canonical phrases found
    """
    if not text:
        return []

    normalized = normalize_phrase(text)
    found_phrases = []

    # Check each canonical phrase and its equivalents
    for canonical, equivalents in PROBLEM_PHRASES.items():
        # Check if canonical phrase appears
        if canonical in normalized:
            found_phrases.append(canonical)
            continue

        # Check if any equivalent appears
        for equivalent in equivalents:
            if equivalent in normalized:
                found_phrases.append(canonical)
                break

    return list(set(found_phrases))  # Deduplicate


def calculate_phrase_similarity(text1, text2):
    """
    Calculate phrase-based similarity between two texts

    Args:
        text1: First text (e.g., PERTS)
        text2: Second text (e.g., KB title/content)

    Returns:
        Number of matching phrases (0-N)
    """
    phrases1 = set(find_matching_phrases(text1))
    phrases2 = set(find_matching_phrases(text2))

    # Count overlapping phrases
    overlap = phrases1.intersection(phrases2)

    return len(overlap)
