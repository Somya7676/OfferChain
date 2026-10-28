import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from blockchain import Blockchain, LedgerError, ChainInvalid, genesis_block, block_hash
from offer_utils import offer_hash

OFFER = {'company_name':'Example Technologies','job_title':'Software Engineer','employment_type':'Full-time', 'work_location':'Indore','salary':'600000 INR per annum','offer_date':'2026-10-28'}

class BlockchainTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'ledger.json'; self.chain = Blockchain(self.path)
    def mutate(self, fn):
        data = json.loads(self.path.read_text()); fn(data); self.path.write_text(json.dumps(data))
    def test_initialization_genesis_deterministic_and_not_offer(self):
        s = self.chain.status(); self.assertTrue(s['valid']); self.assertEqual((s['total_blocks'],s['total_offers']),(1,0))
        self.assertEqual(genesis_block(), genesis_block()); self.assertEqual(genesis_block()['block_hash'],block_hash(genesis_block()))
    def test_registration_link_indices_restart_and_hash(self):
        a = self.chain.register(OFFER); b = self.chain.register(OFFER)
        self.assertEqual((a['index'],b['index']),(1,2)); self.assertEqual(a['previous_hash'],genesis_block()['block_hash']); self.assertEqual(b['previous_hash'],a['block_hash'])
        self.assertEqual(a['offer_hash'],offer_hash(a['offer_id'],OFFER)); self.assertEqual(Blockchain(self.path).find_offer(a['offer_id']),a)
        self.assertIsNone(self.chain.find_offer('OFR-20261028-0000000000000000'))
        self.assertNotEqual(a['offer_hash'],offer_hash(a['offer_id'],dict(OFFER,salary='different')))
        self.assertEqual(a['offer_hash'],offer_hash(a['offer_id'],dict(OFFER,company_name='  Example   Technologies ')))
    def test_duplicate_ids_invalid(self):
        self.chain.register(OFFER); self.chain.register(OFFER)
        def edit(d):
            d['blocks'][2]['offer_id'] = d['blocks'][1]['offer_id']; d['blocks'][2]['block_hash'] = block_hash(d['blocks'][2])
        self.mutate(edit); self.assertFalse(self.chain.status()['valid'])
    def test_collision_retry(self):
        with patch('blockchain.secrets.token_hex', side_effect=['a'*16, 'a'*16, 'b'*16]):
            a=self.chain.register(OFFER); b=self.chain.register(OFFER)
        self.assertNotEqual(a['offer_id'],b['offer_id'])
    def test_tamper_offer_hash(self):
        self.chain.register(OFFER); self.mutate(lambda d:d['blocks'][1].update(offer_hash='f'*64)); self.assertFalse(self.chain.status()['valid'])
        with self.assertRaises(ChainInvalid): self.chain.register(OFFER)
    def test_tamper_content(self):
        self.chain.register(OFFER); self.mutate(lambda d:d['blocks'][1].update(timestamp='2026-01-02T00:00:00+00:00')); self.assertFalse(self.chain.status()['valid'])
    def test_broken_link(self):
        self.chain.register(OFFER)
        def edit(d):
            d['blocks'][1]['previous_hash']='0'*64; d['blocks'][1]['block_hash']=block_hash(d['blocks'][1])
        self.mutate(edit); self.assertFalse(self.chain.status()['valid'])
    def test_malformed_never_reset(self):
        self.path.write_text('{broken'); self.assertFalse(self.chain.status()['valid'])
        with self.assertRaises(ChainInvalid): self.chain.register(OFFER)
        self.assertEqual(self.path.read_text(),'{broken')
    def test_write_failure_not_success(self):
        self.chain.status(); old=self.path.read_text()
        with patch('blockchain.os.replace',side_effect=OSError('disk')):
            with self.assertRaises(LedgerError): self.chain.register(OFFER)
        self.assertEqual(old,self.path.read_text())
    def test_concurrent_threads(self):
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            blocks=list(pool.map(lambda _: Blockchain(self.path).register(OFFER),range(25)))
        self.assertEqual(len({b['offer_id'] for b in blocks}),25); self.assertEqual(self.chain.status()['total_offers'],25); self.assertTrue(self.chain.status()['valid'])
