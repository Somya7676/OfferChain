"""Flask entry point and same-origin JSON API."""
import hmac
import logging
from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge
from blockchain import Blockchain, LedgerError, ChainInvalid
from offer_utils import FIELDS, ValidationError, normalize_offer, offer_hash, validate_offer_id

def create_app(ledger_path=None):
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024
    chain = Blockchain(ledger_path)
    app.extensions['offerchain'] = chain

    def fail(message, status, code='ERROR'):
        return jsonify({'status': code, 'message': message}), status

    def payload():
        if not request.is_json: raise ValidationError('Send a JSON object with Content-Type: application/json.')
        try: data = request.get_json()
        except BadRequest: raise ValidationError('Malformed JSON request.') from None
        if not isinstance(data, dict): raise ValidationError('Request must be a JSON object.')
        return data

    @app.errorhandler(ValidationError)
    def invalid_request(exc): return fail(str(exc), 400, 'INVALID_REQUEST')
    @app.errorhandler(ChainInvalid)
    def invalid_chain(exc): return fail('Ledger integrity failed. Verification and registration are unavailable; inspect the ledger.', 409, 'CHAIN_INVALID')
    @app.errorhandler(LedgerError)
    def ledger_error(exc):
        app.logger.error('Ledger operation failed: %s', exc)
        return fail('The ledger could not be accessed. Check server storage and permissions.', 503, 'LEDGER_ERROR')
    @app.errorhandler(RequestEntityTooLarge)
    def oversized(exc): return fail('Request body is too large.', 413, 'INVALID_REQUEST')

    @app.get('/')
    def home(): return render_template('index.html')

    @app.get('/api/health')
    def health():
        status = chain.status()
        return jsonify({'app': 'running', 'ledger_readable': not (not status['valid'] and status['error'].startswith('Ledger is malformed')), 'chain_valid': status['valid']})

    @app.post('/api/offers')
    def register():
        block = chain.register(normalize_offer(payload()))
        return jsonify({'status':'REGISTERED', 'message':'Offer registered.', 'offer_id':block['offer_id'],
                        'block_index':block['index'], 'timestamp':block['timestamp'],
                        'offer_hash':block['offer_hash'], 'hash_preview':block['offer_hash'][:12]}), 201

    @app.post('/api/offers/verify')
    def verify():
        data = payload()
        if set(data) != set(FIELDS) | {'offer_id'}: raise ValidationError('Provide an Offer ID and exactly the six required offer fields.')
        oid = validate_offer_id(data['offer_id'])
        offer = normalize_offer({k:data[k] for k in FIELDS})
        block = chain.find_offer(oid)
        if block is None:
            return jsonify({'status':'NOT_FOUND','offer_id':oid,'message':'No record exists for this Offer ID.'})
        if hmac.compare_digest(offer_hash(oid, offer), block['offer_hash']):
            return jsonify({'status':'VERIFIED','offer_id':oid,'block_index':block['index'], 'message':'The submitted fields match the registered record.'})
        return jsonify({'status':'MISMATCH','offer_id':oid,'block_index':block['index'], 'message':'The submitted details differ from the registered record. Check the Offer ID and offer information.'})

    @app.get('/api/offers')
    def offers():
        status, blocks = chain.snapshot()
        if not status['valid']: raise ChainInvalid(status['error'])
        return jsonify({'total_offers':status['total_offers'], 'offers':[
            {'offer_id':b['offer_id'], 'block_index':b['index'], 'timestamp':b['timestamp'], 'hash_preview':b['offer_hash'][:12]} for b in reversed(blocks[1:])]})

    @app.get('/api/chain/status')
    def chain_status():
        status = chain.status()
        return jsonify(status), 200 if status['valid'] else 409

    @app.get('/api/chain/blocks')
    def chain_blocks():
        status, blocks = chain.snapshot()
        if not status['valid']: raise ChainInvalid(status['error'])
        return jsonify({'status':status, 'blocks':blocks})
    return app

app = create_app()
application = app

if __name__ == '__main__':
    app.run(debug=True)
