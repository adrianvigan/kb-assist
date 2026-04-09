"""
Product Alias Mapping
Maps D365 product names to PowerBI/KB product names and vice versa
"""

# Product alias mappings
PRODUCT_ALIASES = {
    # VPN Products
    'Trend Micro VPN': ['PUBLIC WI-FI PROTECTION', 'VPN Proxy One Pro', 'WiFi Protection'],
    'PUBLIC WI-FI PROTECTION': ['Trend Micro VPN', 'VPN Proxy One Pro', 'WiFi Protection'],

    # ScamCheck / Mobile Security
    'Trend Micro Scam Check': ['Trend Micro Check', 'MOBILE SECURITY FOR ANDROID', 'MOBILE SECURITY FOR IOS'],
    'Trend Micro Check': ['Trend Micro Scam Check', 'MOBILE SECURITY FOR ANDROID', 'MOBILE SECURITY FOR IOS'],
    'MOBILE SECURITY FOR ANDROID': ['Trend Micro Check', 'Trend Micro Scam Check', 'Mobile Security'],
    'MOBILE SECURITY FOR IOS': ['Trend Micro Check', 'Trend Micro Scam Check', 'Mobile Security'],

    # Maximum Security
    'Maximum Security': ['Titanium', 'Trend Micro Security', 'Internet Security'],
    'Titanium': ['Maximum Security', 'Trend Micro Security'],

    # Home Network Security
    'Home Network Security': ['HOME NETWORK SECURITY', 'HNS'],
    'HOME NETWORK SECURITY': ['Home Network Security', 'HNS'],

    # ID Protection
    'ID Protection': ['Password Manager', 'Trend Micro ID Protection'],
    'Password Manager': ['ID Protection', 'PASSWORD MANAGER'],
    'PASSWORD MANAGER': ['ID Protection', 'Password Manager'],

    # Antivirus for Mac
    'ANTIVIRUS FOR MAC': ['Trend Micro Antivirus for Mac', 'Antivirus One'],
    'Antivirus One': ['ANTIVIRUS FOR MAC', 'ANTIVIRUS ONE'],
    'ANTIVIRUS ONE': ['Antivirus One', 'ANTIVIRUS FOR MAC'],

    # Cleaner One
    'Cleaner One Pro': ['Cleaner One', 'CLEANER ONE'],

    # Mobile Security
    'Mobile Security': ['MOBILE SECURITY FOR ANDROID', 'MOBILE SECURITY FOR IOS'],
}


def get_product_aliases(product_name):
    """
    Get all aliases for a given product name

    Args:
        product_name: Product name from D365 or PowerBI

    Returns:
        List of product aliases (including the original name)
    """
    if not product_name:
        return []

    # Start with the original product name
    aliases = [product_name]

    # Add mapped aliases
    if product_name in PRODUCT_ALIASES:
        aliases.extend(PRODUCT_ALIASES[product_name])

    # Case-insensitive partial matching for common terms
    product_lower = product_name.lower()

    # VPN variations
    if 'vpn' in product_lower:
        aliases.extend(['PUBLIC WI-FI PROTECTION', 'Trend Micro VPN', 'VPN Proxy One Pro'])

    # ScamCheck variations
    if 'scam' in product_lower or 'check' in product_lower:
        aliases.extend(['Trend Micro Check', 'Trend Micro Scam Check', 'MOBILE SECURITY FOR ANDROID', 'MOBILE SECURITY FOR IOS'])

    # Mobile variations
    if 'mobile' in product_lower:
        aliases.extend(['MOBILE SECURITY FOR ANDROID', 'MOBILE SECURITY FOR IOS', 'Trend Micro Check'])

    # Maximum/Titanium variations
    if 'maximum' in product_lower or 'titanium' in product_lower:
        aliases.extend(['Maximum Security', 'Titanium', 'Trend Micro Security'])

    # Home Network variations
    if 'home network' in product_lower or 'hns' in product_lower:
        aliases.extend(['HOME NETWORK SECURITY', 'Home Network Security'])

    # ID Protection variations
    if 'id protection' in product_lower or 'password' in product_lower:
        aliases.extend(['ID Protection', 'Password Manager', 'PASSWORD MANAGER'])

    # Mac Antivirus variations
    if 'mac' in product_lower and 'antivirus' in product_lower:
        aliases.extend(['ANTIVIRUS FOR MAC', 'Antivirus One', 'ANTIVIRUS ONE'])

    # Remove duplicates and return
    return list(set(aliases))


def normalize_product_name(product_name):
    """
    Normalize product name to a canonical form

    Args:
        product_name: Product name from any source

    Returns:
        Normalized product name (PowerBI standard)
    """
    if not product_name:
        return 'Unknown'

    product_lower = product_name.lower()

    # Map to PowerBI canonical names
    if 'vpn' in product_lower or 'wi-fi' in product_lower or 'wifi' in product_lower:
        return 'PUBLIC WI-FI PROTECTION'

    if 'scam' in product_lower or 'check' in product_lower:
        if 'android' in product_lower:
            return 'MOBILE SECURITY FOR ANDROID'
        elif 'ios' in product_lower:
            return 'MOBILE SECURITY FOR IOS'
        else:
            return 'MOBILE SECURITY FOR ANDROID'  # Default to Android

    if 'mobile' in product_lower:
        if 'android' in product_lower:
            return 'MOBILE SECURITY FOR ANDROID'
        elif 'ios' in product_lower:
            return 'MOBILE SECURITY FOR IOS'
        else:
            return 'MOBILE SECURITY FOR ANDROID'

    if 'maximum' in product_lower:
        return 'Titanium'

    if 'titanium' in product_lower:
        return 'Titanium'

    if 'home network' in product_lower or 'hns' in product_lower:
        return 'HOME NETWORK SECURITY'

    if 'id protection' in product_lower:
        return 'ID Protection'

    if 'password' in product_lower:
        return 'PASSWORD MANAGER'

    if 'mac' in product_lower and 'antivirus' in product_lower:
        return 'ANTIVIRUS FOR MAC'

    if 'cleaner' in product_lower:
        return 'Cleaner One Pro'

    # Return as-is if no mapping found
    return product_name


def is_same_product(product1, product2):
    """
    Check if two product names refer to the same product

    Args:
        product1: First product name
        product2: Second product name

    Returns:
        True if they're the same product, False otherwise
    """
    if not product1 or not product2:
        return False

    # Exact match (case-insensitive)
    if product1.lower() == product2.lower():
        return True

    # Check if they share aliases
    aliases1 = set([p.lower() for p in get_product_aliases(product1)])
    aliases2 = set([p.lower() for p in get_product_aliases(product2)])

    # If there's any overlap in aliases, they're the same product
    return bool(aliases1.intersection(aliases2))
