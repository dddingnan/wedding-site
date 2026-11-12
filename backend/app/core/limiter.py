from slowapi import Limiter
from slowapi.util import get_remote_address

# Invite codes are short, so the lookup endpoint is the one worth protecting
# from brute-force guessing. Keyed by client IP.
limiter = Limiter(key_func=get_remote_address)
