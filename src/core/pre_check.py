from typing import List

def check_student_identifiers(
    body: str,
    register_number: str = None,
    email: str = None,
    neopat_id: str = None,
    full_name: str = None
) -> bool:
    """Performs deterministic case-insensitive pre-checks in the email body for student identifiers.
    
    Checks for:
    - Register Number substring match
    - Email address substring match
    - NeoPAT ID substring match
    - Tokenized student name matching (requires at least 2 name tokens of length > 1 to match)
    
    Returns:
        True if any match is verified, otherwise False.
    """
    if not body:
        return False
        
    body_lower = body.lower()
    
    # 1. Check Register Number
    if register_number and register_number.strip():
        if register_number.strip().lower() in body_lower:
            return True
            
    # 2. Check Email Address
    if email and email.strip():
        if email.strip().lower() in body_lower:
            return True
            
    # 3. Check NeoPAT ID
    if neopat_id and neopat_id.strip():
        if neopat_id.strip().lower() in body_lower:
            return True
            
    # 4. Check Student Name (token-based check to prevent middle name/initial mismatches)
    if full_name and full_name.strip():
        # Split the full name into tokens, ignoring single-letter initials (length <= 1)
        tokens = [token.lower() for token in full_name.strip().split() if len(token) > 1]
        
        # If the student's name only yields 1 token after filtering (or none), fall back to matching all tokens
        if len(tokens) < 2:
            fallback_tokens = [token.lower() for token in full_name.strip().split() if len(token) > 0]
            if fallback_tokens and all(token in body_lower for token in fallback_tokens):
                return True
        else:
            # Count how many name tokens are present in the body
            matched_tokens = sum(1 for token in tokens if token in body_lower)
            if matched_tokens >= 2:
                return True
                
    return False
