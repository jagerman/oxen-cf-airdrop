import string
from Cryptodome.Hash import keccak

all_hex = set(string.hexdigits)
lc_hex = set('0123456789abcdef')
uc_hex = set('0123456789ABCDEF')

"""
Validates whether the given string is an ETH address.

- Must be 0x followed by 40 all hex digits
- If not all-lower-case or all-upper-case then caps-based checksum must match
"""
def validate(addr):
    if not addr.startswith('0x'):
        return False
    addr = addr[2:]
    if len(addr) != 40 or not all(x in all_hex for x in addr):
        return False
    if all(x in lc_hex for x in addr) or all(x in uc_hex for x in addr):
        return True

    # Mixed case: do checksum casing (see EIP-55)
    keccak_hash = keccak.new(digest_bits=256)
    keccak_hash.update(addr.lower().encode())
    addrhash = keccak_hash.hexdigest()
    return all(c.isdigit() or (c.isupper() if int(addrhash[i], 16) >= 8 else c.islower())
            for i, c in enumerate(addr))
