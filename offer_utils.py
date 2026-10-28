"""Canonical offer validation and hashing. No original offer data is persisted."""
import hashlib
import json
import re
import unicodedata
from datetime import date

FIELDS = ('company_name', 'job_title', 'employment_type', 'work_location', 'salary', 'offer_date')
EMPLOYMENT_TYPES = ('Full-time', 'Part-time', 'Internship', 'Contract')
LIMITS = {'company_name': 120, 'job_title': 120, 'employment_type': 20,
          'work_location': 120, 'salary': 120, 'offer_date': 10}
OFFER_ID_RE = re.compile(r'OFR-\d{8}-[A-F0-9]{16}\Z')

class ValidationError(ValueError):
    pass

def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)

def sha256_json(value):
    return hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()

def normalize_offer(data):
    if not isinstance(data, dict):
        raise ValidationError('Offer must be a JSON object.')
    if set(data) != set(FIELDS):
        raise ValidationError('Provide exactly the six required offer fields; unexpected fields are not allowed.')
    result = {}
    for key in FIELDS:
        value = data[key]
        if not isinstance(value, str):
            raise ValidationError(f'{key} must be text.')
        # Also bound input before normalization to avoid excessive work.
        if len(value) > LIMITS[key] * 4:
            raise ValidationError(f'{key} is too long.')
        value = ' '.join(unicodedata.normalize('NFC', value).split())
        if not value or len(value) > LIMITS[key]:
            raise ValidationError(f'{key} is required and must be at most {LIMITS[key]} characters.')
        # Reject control and surrogate characters not removed by whitespace normalization.
        if any(unicodedata.category(c) in ('Cc', 'Cs') for c in value):
            raise ValidationError(f'{key} contains unsupported characters.')
        result[key] = value
    if result['employment_type'] not in EMPLOYMENT_TYPES:
        raise ValidationError('Choose a valid employment type.')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', result['offer_date']):
        raise ValidationError('Offer date must be a real date in YYYY-MM-DD format.')
    try:
        date.fromisoformat(result['offer_date'])
    except ValueError:
        raise ValidationError('Offer date must be a real date in YYYY-MM-DD format.') from None
    return result

def validate_offer_id(value):
    if not isinstance(value, str) or not OFFER_ID_RE.fullmatch(value):
        raise ValidationError('Offer ID must have the format OFR-YYYYMMDD- followed by 16 uppercase hexadecimal characters.')
    return value

def offer_hash(offer_id, offer):
    validate_offer_id(offer_id)
    return sha256_json({'schema_version': 1, 'offer_id': offer_id, 'offer': normalize_offer(offer)})
