#!/usr/bin/env python3

import flask
from flask_cors import CORS
import json
import psycopg2
import requests
from datetime import timezone
from omq import FutureJSON, omq_connection
import config
import ethaddr
import traceback

psql = psycopg2.connect(**config.pgsql_connect_opts)
app = flask.Flask(__name__)
CORS(app)


def pinball(score):
    """
    Convert a database score number (which is 1.0, 1.2, or 1.4 per snapshot per full SN stake) into
    a "pinball" score, which is 1000.0 per day per full SN (or 1200 or 1400 for bonus).
    """
    return None if score is None else score * 1000 / 24  # 1000 points per day, 24 snapshots per day


def daily_shares(shares):
    """
    Converts a raw # of shares value (which is 1 per snapshot per full SN, thus 24/day) into a daily value
    """
    return None if shares is None else shares / 24


@app.route('/scores')
def scores():
    wallets = {}
    snapshots = 0
    total_shares = 0.0
    total_score = 0.0
    with psql:
        with psql.cursor() as cur:
            cur.execute("SELECT SUM(shares), SUM(score) FROM aggregate_shares")
            total_shares, total_score = cur.fetchone()
            cur.execute("SELECT COUNT(*) FROM snapshots")
            snapshots = cur.fetchone()[0]
            cur.execute("SELECT address, shares, score, snapshots FROM aggregate_shares JOIN wallets ON wallet = wallets.id")
            for row in cur:
                wallets[row[0]] = {'shares': daily_shares(row[1]), 'score': pinball(row[2]), 'snapshots': row[3]}

    return flask.jsonify({
        'wallets': wallets,
        'total_snapshots': snapshots,
        'global_shares': daily_shares(total_shares),
        'global_score': pinball(total_score),
    })


@app.route('/snapshots')
def snapshots():
    snapshots = []
    with psql:
        with psql.cursor() as cur:
            cur.execute("""
                SELECT height, blockhash, date,
                    (SELECT COUNT(*) FROM wallet_snapshot_shares WHERE wallet_snapshot_shares.height = snapshots.height) AS wallets
                FROM snapshots
                ORDER BY height DESC
                """)
            for row in cur:
                snapshots.append({
                    'height': row[0],
                    'hash': row[1],
                    'timestamp': row[2].astimezone(timezone.utc).isoformat(),
                    'wallets': row[3],
                    })

    return flask.jsonify({ 'snapshots': snapshots })


@app.route('/score/<wallet>')
def wallet_score(wallet):
    with psql:
        with psql.cursor() as cur:
            cur.execute("""
                SELECT shares, score, snapshots FROM aggregate_shares
                WHERE wallet = (
                    SELECT id FROM wallets WHERE
                        address = %(wallet)s OR lower(destination) = lower(%(wallet)s)
                    LIMIT 1)
                """,
                {'wallet': wallet}
            )
            row = cur.fetchone()
            if row:
                return flask.jsonify({ 'shares': daily_shares(row[0]), 'score': pinball(row[1]), 'snapshots': row[2] })
    return flask.jsonify({ 'error': 'Wallet not found' })


@app.route('/scores/<wallet>')
def wallet_scores(wallet):
    snapshots = []
    with psql:
        with psql.cursor() as cur:
            cur.execute("""
                SELECT height, shares, score FROM wallet_shares
                WHERE wallet = (
                    SELECT id FROM wallets WHERE
                        address = %(wallet)s OR lower(destination) = lower(%(wallet)s)
                    LIMIT 1)
                ORDER BY height DESC
                """,
                {'wallet': wallet}
            )
            for row in cur:
                snapshots.append({'height': row[0], 'shares': daily_shares(row[1]), 'score': pinball(row[2])})

    return flask.jsonify({ 'address': wallet, 'snapshots': snapshots })


def json_error(msg):
    return flask.jsonify({ 'error': msg })


@app.route('/register', methods=['POST'])
def register_wallet():
    """
    Registers a wallet (or updates an existing destination address).  We need a json request
    containing three keys:
    - address -- the OXEN wallet address of the contributor
    - destination -- a valid Ethereum address where Chainflip tokens are to be received
    - signature -- a signature of the destination address signed by the OXEN wallet (for GUI:
                   Advanced -> Sign/Verify; for cli "sign_value")

    Returns either:
        { "error": "Some error string" }
    or:
        { "result": { "added": true } }
    """

    try:
        req = flask.request.get_json(force=True)
        r = requests.post(config.oxen_wallet_rpc, json={
            "jsonrpc": "2.0", "id": "0",
            "method": "validate_address",
            "params": { "address": req['address'] }})
        r = r.json()['result']
        if not r['valid']:
            return json_error('Invalid OXEN wallet address')
        if r['integrated']:
            return json_error('Integrated OXEN wallet addresses are not accepted')
        if r['subaddress']:
            return json_error('OXEN subaddresses not accepted')

        if not ethaddr.validate(req['destination']):
            return json_error('Invalid ETH wallet address')

        r = requests.post(config.oxen_wallet_rpc, json={
            "jsonrpc": "2.0", "id": "0",
            "method": "verify",
            "params": { "address": req['address'], "data": req['destination'], "signature": req['signature'] }})
        r = r.json()['result']
        if not r['good']:
            return json_error('Invalid OXEN wallet signature: check the wallet and destination addresses and try again')

        with psql:
            with psql.cursor() as cur:
                cur.execute("""
                    INSERT INTO wallets (address, destination, signature) VALUES (%(addr)s, %(dest)s, %(sig)s)
                    ON CONFLICT (address) DO UPDATE SET destination = %(dest)s, signature = %(sig)s
                    """,
                    { 'addr': req['address'], 'dest': req['destination'], 'sig': req['signature'] })

        return flask.jsonify({ 'result': { 'added': True } })
    except KeyError as e:
        return json_error('Failed to register: missing "{}" parameter'.format(e.args[0]))
    except requests.RequestException as e:
        return json_error('Failed to communicate with local wallet')
    except Exception as e:
        traceback.print_exc()
        return json_error('Internal error: {}'.format(e))
    return json_error('Unknown error')
