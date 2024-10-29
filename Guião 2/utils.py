def dht_hash(text, seed=0, maximum=2**10):
    """ FNV-1a Hash Function. """
    fnv_prime = 16777619
    offset_basis = 2166136261
    h = offset_basis + seed
    for char in text:
        h = h ^ ord(char)
        h = h * fnv_prime
    return h % maximum


def contains(begin, end, node):
    if not end or not begin:
        return False

    if begin > end:
        return (begin < node < 1024) or (0 <= node <= end)
    else:
        return begin < node <= end

