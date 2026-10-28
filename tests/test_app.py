import json
import tempfile
import unittest
from pathlib import Path
from app import create_app
from test_blockchain import OFFER

class APITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'ledger.json'; self.client=create_app(self.path).test_client()
    def register(self):
        response=self.client.post('/api/offers',json=OFFER); self.assertEqual(response.status_code,201); return response.json
    def test_home_health(self):
        self.assertEqual(self.client.get('/').status_code,200); self.assertTrue(self.client.get('/api/health').json['ledger_readable'])
    def test_register_verify_counts(self):
        a=self.register(); body=dict(OFFER,offer_id=a['offer_id'])
        self.assertEqual(self.client.post('/api/offers/verify',json=body).json['status'],'VERIFIED')
        self.assertEqual(self.client.post('/api/offers/verify',json=dict(body,salary='other')).json['status'],'MISMATCH')
        self.assertEqual(self.client.post('/api/offers/verify',json=dict(body,offer_id='OFR-20261028-0000000000000000')).json['status'],'NOT_FOUND')
        self.assertEqual(self.client.get('/api/offers').json['total_offers'],1)
        self.assertEqual(self.client.get('/api/chain/status').json['total_blocks'],2)
        self.assertEqual(len(self.client.get('/api/chain/blocks').json['blocks']),2)
    def test_bad_requests(self):
        for data in [dict(OFFER, employment_type='No'),dict(OFFER,offer_date='2026-02-30'), {'company_name':'x'},dict(OFFER,offer_id='caller chosen')]:
            with self.subTest(data=data): self.assertEqual(self.client.post('/api/offers',json=data).status_code,400)
        self.assertEqual(self.client.post('/api/offers',data='{bad',content_type='application/json').status_code,400)
        self.assertEqual(self.client.post('/api/offers',data='x'*20000,content_type='application/json').status_code,413)
    def test_corrupt_chain_blocks_registration_and_verification(self):
        a=self.register(); d=json.loads(self.path.read_text()); d['blocks'][1]['offer_hash']='f'*64; self.path.write_text(json.dumps(d))
        self.assertEqual(self.client.post('/api/offers/verify',json=dict(OFFER,offer_id=a['offer_id'])).json['status'],'CHAIN_INVALID')
        self.assertEqual(self.client.post('/api/offers',json=OFFER).status_code,409)
        self.assertEqual(self.client.get('/api/chain/status').status_code,409)
    def test_malformed_ledger_not_reset(self):
        self.path.write_text('invalid'); self.assertEqual(self.client.get('/api/chain/status').status_code,409)
        self.assertEqual(self.client.post('/api/offers',json=OFFER).json['status'],'CHAIN_INVALID'); self.assertEqual(self.path.read_text(),'invalid')
