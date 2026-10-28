"""A single-process, file-backed teaching ledger; not a distributed blockchain."""
import json
import os
import re
import secrets
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from offer_utils import sha256_json, offer_hash, normalize_offer, OFFER_ID_RE

ZERO = '0' * 64
FIELDS = {'index', 'timestamp', 'offer_id', 'offer_hash', 'previous_hash', 'block_hash'}
HEX = re.compile(r'[0-9a-f]{64}\Z')
LOCKS = {}
LOCKS_GUARD = threading.Lock()

class LedgerError(Exception):
    """Ledger could not be safely read or written."""

class ChainInvalid(LedgerError):
    pass

def block_hash(block):
    return sha256_json({k: v for k, v in block.items() if k != 'block_hash'})

def genesis_block():
    block = {'index': 0, 'timestamp': '2026-01-01T00:00:00+00:00', 'offer_id': 'GENESIS',
             'offer_hash': ZERO, 'previous_hash': ZERO}
    block['block_hash'] = block_hash(block)
    return block

class Blockchain:
    def __init__(self, ledger_path=None):
        self.path = Path(ledger_path or Path(__file__).resolve().parent / 'data' / 'ledger.json').resolve()
        # All instances referring to the same file share one in-process lock.
        with LOCKS_GUARD:
            self.lock = LOCKS.setdefault(str(self.path), threading.Lock())

    def _save(self, ledger):
        tmp = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent,
                    prefix='.ledger-', suffix='.tmp', delete=False) as f:
                tmp = f.name
                json.dump(ledger, f, ensure_ascii=False, indent=2, allow_nan=False)
                f.write('\n')
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
        except (OSError, ValueError) as exc:
            raise LedgerError('Unable to write the ledger. Check storage and permissions.') from exc
        finally:
            if tmp and os.path.exists(tmp):
                try: os.unlink(tmp)
                except OSError: pass

    def _load(self):
        try:
            if not self.path.exists():
                self._save({'schema_version': 1, 'blocks': [genesis_block()]})
            with self.path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError, RecursionError) as exc:
            raise ChainInvalid('Ledger is malformed; inspect it without overwriting it.') from exc
        except OSError as exc:
            raise LedgerError('Unable to read the ledger. Check storage and permissions.') from exc

    @staticmethod
    def _validate(ledger):
        blocks = ledger.get('blocks') if isinstance(ledger, dict) else None
        n = len(blocks) if isinstance(blocks, list) else 0
        def invalid(msg):
            return {'valid': False, 'total_blocks': n, 'total_offers': max(0, n - 1), 'error': msg}
        if (not isinstance(ledger, dict) or set(ledger) != {'schema_version', 'blocks'}
                or type(ledger['schema_version']) is not int or ledger['schema_version'] != 1
                or not isinstance(blocks, list) or not blocks):
            return invalid('Invalid ledger schema or missing genesis block.')
        seen = set()
        for i, b in enumerate(blocks):
            if not isinstance(b, dict) or set(b) != FIELDS:
                return invalid(f'Block {i} has invalid fields.')
            if type(b['index']) is not int or b['index'] != i:
                return invalid(f'Block {i} has an invalid index.')
            if not isinstance(b['timestamp'], str):
                return invalid(f'Block {i} has an invalid timestamp.')
            try:
                dt = datetime.fromisoformat(b['timestamp'])
                if dt.tzinfo is None or dt.utcoffset() != timezone.utc.utcoffset(dt):
                    raise ValueError
            except (ValueError, OverflowError):
                return invalid(f'Block {i} has an invalid UTC timestamp.')
            for key in ('offer_hash', 'previous_hash', 'block_hash'):
                if not isinstance(b[key], str) or not HEX.fullmatch(b[key]):
                    return invalid(f'Block {i} has an invalid {key}.')
            if i == 0:
                if b != genesis_block(): return invalid('Genesis block is invalid.')
            else:
                if not isinstance(b['offer_id'], str) or not OFFER_ID_RE.fullmatch(b['offer_id']):
                    return invalid(f'Block {i} has an invalid Offer ID.')
                if b['offer_id'] in seen: return invalid(f'Block {i} has a duplicate Offer ID.')
                seen.add(b['offer_id'])
                if b['previous_hash'] != blocks[i-1]['block_hash']:
                    return invalid(f'Block {i} has a broken previous-hash link.')
            try:
                if block_hash(b) != b['block_hash']: return invalid(f'Block {i} has a hash mismatch.')
            except (ValueError, TypeError, UnicodeEncodeError):
                return invalid(f'Block {i} contains invalid data.')
        return {'valid': True, 'total_blocks': n, 'total_offers': n - 1, 'error': None}

    def snapshot(self):
        with self.lock:
            try:
                ledger = self._load()
            except ChainInvalid as exc:
                return {'valid': False, 'total_blocks': 0, 'total_offers': 0, 'error': str(exc)}, []
            status = self._validate(ledger)
            # Do not return unvalidated metadata when the structure has been tampered with.
            return status, ledger['blocks'] if status['valid'] else []

    def status(self):
        return self.snapshot()[0]

    def find_offer(self, offer_id):
        status, blocks = self.snapshot()
        if not status['valid']: raise ChainInvalid(status['error'])
        return next((b for b in blocks[1:] if b['offer_id'] == offer_id), None)

    def register(self, offer):
        offer = normalize_offer(offer)
        with self.lock:
            ledger = self._load()
            status = self._validate(ledger)
            if not status['valid']: raise ChainInvalid(status['error'])
            blocks = ledger['blocks']
            ids = {b['offer_id'] for b in blocks}
            while True:
                oid = 'OFR-' + datetime.now(timezone.utc).strftime('%Y%m%d') + '-' + secrets.token_hex(8).upper()
                if oid not in ids: break
            block = {'index': len(blocks), 'timestamp': datetime.now(timezone.utc).isoformat(),
                     'offer_id': oid, 'offer_hash': offer_hash(oid, offer), 'previous_hash': blocks[-1]['block_hash']}
            block['block_hash'] = block_hash(block)
            blocks.append(block)
            self._save(ledger)
            return block
