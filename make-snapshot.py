#!/usr/bin/env python3

import psycopg2
import config
from omq import omq_connection, FutureJSON
from datetime import datetime, timezone, timedelta

omq, oxend = omq_connection()
psql = psycopg2.connect(**config.pgsql_connect_opts)

with psql:
    with psql.cursor() as cur:
        cur.execute("SELECT MAX(date) FROM snapshots")
        #if datetime.now(timezone.utc) - cur.fetchone()[0] < timedelta(minutes=59.5):
#        if datetime.now(timezone.utc) - cur.fetchone()[0] < timedelta(seconds=59.5):
#            raise RuntimeError("Not time to snapshot yet")

        cur.execute("SELECT address, id FROM wallets")
        wallets = dict(cur.fetchall())

        if not wallets:
            raise RuntimeError("no wallets in database!")

        sns = FutureJSON(omq, oxend, 'rpc.get_service_nodes', cache_seconds=None, args={
            "fields": {x: True for x in ("contributors", "staking_requirement", "block_hash", "height")},
            "active_only": True
        }).get()
        if sns is None:
            raise RuntimeError("get_service_nodes request failed!")

        height = sns["height"]

        shares = {}

        for sn in sns['service_node_states']:
            for contr in sn["contributors"]:
                addr = contr['address']
                if addr in wallets:
                    if addr not in shares:
                        shares[addr] = 0.0
                    shares[addr] += contr['amount'] / sn['staking_requirement']

        if not shares:
            raise RuntimeError("found no shares, something getting wrong!")

        cur.execute("INSERT INTO snapshots (height, blockhash) VALUES (%s, %s)", (height, sns["block_hash"]))
        for addr, sh in shares.items():
            cur.execute("INSERT INTO wallet_snapshot_shares (wallet, height, shares) VALUES (%s, %s, %s)",
                    (wallets[addr], height, sh))
        cur.execute("REFRESH MATERIALIZED VIEW aggregate_shares")

print("Snapshot created!")
