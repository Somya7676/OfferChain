import unittest
from offer_utils import normalize_offer, offer_hash, ValidationError
from test_blockchain import OFFER

class OfferTests(unittest.TestCase):
    def test_unicode_and_whitespace(self):
        a=dict(OFFER, company_name=' Cafe\u0301  Company '); b=dict(OFFER,company_name='Café Company')
        self.assertEqual(normalize_offer(a), normalize_offer(b)); self.assertEqual(offer_hash('OFR-20261028-0123456789ABCDEF',a),offer_hash('OFR-20261028-0123456789ABCDEF',b))
    def test_changes_and_id(self):
        oid='OFR-20261028-0123456789ABCDEF'; h=offer_hash(oid,OFFER)
        for key in OFFER:
            val = {'employment_type':'Contract','offer_date':'2026-10-27'}.get(key, 'Changed')
            self.assertNotEqual(h,offer_hash(oid,dict(OFFER, **{key:val})))
        self.assertNotEqual(h,offer_hash('OFR-20261028-0123456789ABCDE0',OFFER))
    def test_reject_bad_input(self):
        for data in [dict(OFFER, salary=2), dict(OFFER,offer_date='2026-02-30'),dict(OFFER,employment_type='full-time'), dict(OFFER, extra='x'), dict(OFFER, job_title='x'*121), {k:v for k,v in OFFER.items() if k!='salary'}]:
            with self.subTest(data=data), self.assertRaises(ValidationError): normalize_offer(data)
