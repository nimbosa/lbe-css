# coding: utf8
# LBE - Lite Block Explorer
# Author: hellcatz <http://github.com/hellcatz>
# Author: Ondrej Sika <ondrej@ondrejsika.com>
# License: MIT <http://ondrejsika.com/license/mit.txt>

import argparse
import binascii
import datetime
import json

from StringIO import StringIO
from flask import Flask, render_template
from jsonrpc_requests import Server, TransportError, ProtocolError

from utils import chunks, var_int_deserialize

parser = argparse.ArgumentParser('LBE - Light Blockchain Explorer (CSS Enhanced)')
parser.add_argument('HOST', type=str)
parser.add_argument('PORT', type=int)
parser.add_argument('XCOIND_HOST', type=str)
parser.add_argument('XCOIND_PORT', type=int)
parser.add_argument('XCOIND_USER', type=str)
parser.add_argument('XCOIND_PASSWORD', type=str)
parser.add_argument('--coin', type=str, default='')
parser.add_argument('--n-last-blocks', type=int, default=100)
parser.add_argument('--equihash', type=int, default=1)
parser.add_argument('--debug', action='store_true')

args = parser.parse_args()

from datetime import tzinfo, timedelta
class simple_utc(tzinfo):
    def tzname(self):
        return "UTC"
    def utcoffset(self, dt):
        return timedelta(0)

class DummyCache(object):
    def set(self, key, val):
        pass

    def get(self, key):
        return None

class LocalCache(object):
    _storage = None

    def __init__(self):
        self._storage = {}

    def set(self, key, val):
        self._storage[key] = val

    def get(self, key):
        return self._storage.get(key)


class Xcoind(object):
    _rpc = None
    _cache = None

    def __init__(self, host, port, user, password, cache=None):
        self._rpc_server = Server('http://%s:%s' % (host, port), auth=(user, password))
        self._cache = cache if cache else LocalCache()

    def rpc(self, method, *params):
        cachekey = 'rpc__%s_%s' % (method, str(params))
        resp = self._cache.get(cachekey)
        if resp:
            return resp
        resp = self._rpc_server.send_request(method, False, params)
        self._cache.set(cachekey, resp)
        return resp

    def getbestblockhash(self):
        return self.rpc('getbestblockhash')

    def getblock(self, hash):
        block = self.rpc('getblock', hash, True)
        block['version_hex'] = hex(block['version'])
        block['version_bin'] = bin(block['version'])
        return block

    def getlastnblocks(self, limit):
        lastblockhash = self.getbestblockhash()
        cachekey = 'getlastnblocks__%s__%s' % (lastblockhash, limit)

        blocks = self._cache.get(cachekey)
        if blocks:
            return blocks

        last = self.getblock(lastblockhash)
        blocks = [last]
        for i in range(limit):
            if not 'previousblockhash' in last:
                break
            last = self.getblock(last['previousblockhash'])
            blocks.append(last)

        self._cache.set(cachekey, blocks)
        return blocks

    def gettx(self, tx_hash):
        try:
            raw = self.rpc('getrawtransaction', tx_hash)
        except (TransportError, ProtocolError), e:
            raise ProtocolError('getrawtransaction ' + tx_hash + '\n' + 'Error ' + json.JSONEncoder().encode(e.args))
            
        return self.rpc('decoderawtransaction', raw)

    def gettxs(self, tx_hashes):
        cachekey = 'gettxs__%s' % str(tx_hashes)
        txs = self._cache.get(cachekey)
        if txs:
            return txs

        txs = []
        for tx_hash in tx_hashes:
            tx = self.gettx(tx_hash)
            txs.append(tx)

        self._cache.set(cachekey, txs)
        return txs

    def getsimpletx(self, txid):
        tx = self.gettx(txid)
        vins = []
        if tx['vin']:
            if 'coinbase' in tx['vin'][0]:
                coinbase = tx['vin'][0]['coinbase']
                coinbase_text = ''.join([i if ord(i) < 128 else '.' for i in binascii.unhexlify(coinbase)])
            else:
                coinbase = None
                coinbase_text = None
                for vin in tx['vin']:
                    try:
                        in_tx = self.gettx(vin['txid'])
                    except (TransportError, ProtocolError), e:
                        in_tx = None
                    if in_tx:
                        for in_vout in in_tx['vout']:
                            if vin['vout'] == in_vout['n']:
                                vins.append({
                                    'address': in_vout['scriptPubKey']['addresses'][0] if 'addresses' in in_vout['scriptPubKey'] else None,
                                    'value': in_vout['value'],
                                })
                    else:
                        vins.append({
                            'address': '???',
                            'value': '???',
                            })
        else:
            coinbase = None
            coinbase_text = None

        vouts = []
        for vout in tx['vout']:
            vouts.append({
                'address': vout['scriptPubKey']['addresses'][0] if 'addresses' in vout['scriptPubKey'] else None,
                'value': vout['value'],
            })
        return {
            'txid': txid,
            'is_coinbase': bool(coinbase),
            'coinbase': coinbase,
            'coinbase_text': coinbase_text,
            'vin': vins,
            'vout': vouts,
            'tx': tx,
            }
            
class Zcashd(Xcoind):
    def getblock(self, hash):
        block = super(Zcashd, self).getblock(hash)
        raw_block = self.rpc('getblock', hash, False)
        block.update(self._parse_raw_block_header(raw_block))
        return block

    @staticmethod
    def _parse_raw_block_header(header):
        nonce = header[2*108:2*140]
        nonce_text = ''.join([i if ord(i) < 128 else '.' for i in binascii.unhexlify(nonce)])
        solution_size_hex = header[2*140:2*143]
        solution_size_int = var_int_deserialize(StringIO(binascii.unhexlify(solution_size_hex)))
        solution = header[2*143:2*(143+solution_size_int)]

        return {
            'nonce': nonce,
            'nonce_text': nonce_text,
            'solution_size': solution_size_int,
            'solution_size_hex': solution_size_hex,
            'solution': solution,
            'solution_br': chunks(solution, 128),
            'raw': header,
}

eqhashBased = args.equihash
if eqhashBased > 0:
    xcoind = Zcashd(args.XCOIND_HOST, args.XCOIND_PORT, args.XCOIND_USER, args.XCOIND_PASSWORD, cache=DummyCache())
else:
    xcoind = Xcoind(args.XCOIND_HOST, args.XCOIND_PORT, args.XCOIND_USER, args.XCOIND_PASSWORD, cache=DummyCache())
    

app = Flask(__name__)
app.debug = args.debug

@app.template_filter('iso_time')
def timeisotime(s):
    return datetime.datetime.utcfromtimestamp(s).replace(tzinfo=simple_utc()).isoformat()

@app.template_filter('formated_time')
def timectime(s):
    return datetime.datetime.utcfromtimestamp(s).replace(tzinfo=simple_utc())


@app.route('/')
def index():
    try:
        blocks = xcoind.getlastnblocks(args.n_last_blocks)
    except (TransportError, ProtocolError), e:
        return render_template('error_xcoind.html', error=e, coin=args.coin)
        
    return render_template('index.html', blocks=blocks, coin=args.coin, eqhash=eqhashBased)


@app.route('/block/<hash>')
def block(hash):
    try:
        block = xcoind.getblock(hash)
        coinbase = xcoind.getsimpletx(block['tx'][0])
    except (TransportError, ProtocolError), e:
        return render_template('error_xcoind.html', error=e, coin=args.coin)

    return render_template('block.html', block=block, coinbase=coinbase, coin=args.coin, eqhash=eqhashBased)

@app.route('/tx/<hash>')
def tx(hash):
    try:
        tx = xcoind.getsimpletx(hash)
    except (TransportError, ProtocolError), e:
        return render_template('error_xcoind.html', error=e, coin=args.coin, eqhash=eqhashBased)

    return render_template('tx.html', tx=tx, coin=args.coin)

if __name__ == '__main__':
    app.run(host=args.HOST, port=args.PORT)
