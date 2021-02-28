# Configuration options
#


# OMQ RPC endpoint of oxend; can be a unix socket 'ipc:///path/to/oxend.sock' (preferred) or a tcp
# socket 'tcp://127.0.0.1:5678'.  Typically you want this running with admin permission.
oxend_rpc = 'ipc:///home/jagerman/.oxen/oxend.sock'

# Some running oxen wallet rpc which we can use for signature verification.  It has to have an
# actual opened wallet (which is stupid), but doesn't have to (and shouldn't!) have anything in the
# wallet.
oxen_wallet_rpc = 'http://127.0.0.1:22026/json_rpc'

# postgresql connect options
pgsql_connect_opts = {
    "dbname": "jagerman",
}
