import re
import hashlib
from collections import Counter

THRESHOLD = 3  # Hyper-parameter (convention for near-dup threshold is 3~10)

def compute_hash_value(content: str) -> str:
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def tokenize(text: str) -> list[str]:
    return re.findall(r'\b[a-zA-Z]{1,}\b', text.lower())


def compute_simhash(tokens: list[str], hashbits: int = 128) -> int: 
    """
    Constraints: Number of entries in "sumed_weights vector" and "hashbits" must be equal; otherwise, causes Indexerror
    """
    token_freq_table: dict[str, int] = Counter(tokens)

    # Convert all {token: freq} to {token: hash_value}  # hash value is token in binary (O(n) where n is number of unique tokens)
    token_hashed: dict[str, int] = convertToHash(token_freq_table)

    # Vector formed by summing weights
    summed_weights: list[int] = [0] * hashbits  # ith index is ith bit of vector of summing weights

    # Calculate summed weights
    for index in range(len(summed_weights)):
        for tok, hsh in token_hashed.items():
            weight = token_freq_table[tok]  # weight = freq of token
            if bin(hsh)[2:].zfill(128)[index] == '0':  # pad upper bits to 0
                summed_weights[index] -= weight
            else:  # if bit is 1
                summed_weights[index] += weight

    # Convert to 128-bit binary (saved as int type)
    fingerprint = sum((v > 0) << (hashbits - 1 - i) for i, v in enumerate(summed_weights))

    return fingerprint


def convertToHash(freq_table: dict[str, int]) -> dict[str, int]:
    """ Return: Dict of which keys are tokens
            and values are tokens converted in decimal hash values"""
    toReturn = dict()
    for token in freq_table.keys():
        toReturn[token] = int(compute_hash_value(token), 16)
    return toReturn


def calculate_hash_distance(hash1: int, hash2: int) -> int: 
    return bin(hash1 ^ hash2).count('1')


