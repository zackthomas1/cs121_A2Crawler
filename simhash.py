from bs4 import BeautifulSoup
from tokenizer import Tokenize, ComputeTokenFrequencies
import hashlib

def compute_hash_value(content: str) -> str:
    return hashlib.md5(content.encode('utf-8')).hexdigest()


'''
# Uncomment to activate Simhash ver.2 (code essence based on Lecture slide 3.1 p.45-46)
def compute_simhash(text: str, hashbits: int = 128) -> int: 
    """
    Constraints: Number of entries in sumed_weights vector and hashbits must equal; otherwise, causes Indexerror
    """
    # Create a list of tokens(words) in the html text
    #   and compute the frequence of each token
    tokens: list[str] = Tokenize(text)
    token_freq_table = {}
    ComputeTokenFrequencies(tokens, token_freq_table)  # token_freq_table updated as {token: freq}

    ## Initialize all hashbits to 0
    #vector = [0] * hashbits

    # Convert all {token: freq} to {token: hash_value}  # hash value is token in binary (O(n) where n is number of unique tokens)
    token_hashed: dict[str, int] = convertToHash(token_freq_table)

    # Vector formed by summing weights
    summed_weights: list[int] = [0] * hashbits  # ith index is ith bit of vector of summing weights

    # Calculate summed weights
    for index in range(len(summed_weights)):
        for tok, hsh in token_hashed.items():
            weight = token_freq_table[tok]  # weight = freq of token
            if bin(hsh)[2:][index] == '0':
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
'''


def compute_simhash(text: str, hashbits: int = 128) -> int: 
    """
    Constraints: Number of entries in sumed_weights vector and hashbits must equal; otherwise, causes Indexerror
    """
    # Create a list of tokens(words) in the html text
    # and compute the frequence of each token
    tokens: list[str] = Tokenize(text)
    # token_freq_table = {}
    # ComputeTokenFrequencies(tokens, token_freq_table)  # token_freq_table updated as {token: freq}

    ## Initialize all hashbits to 0
    vector = [0] * hashbits
    
    for token in tokens:
        # Compute a hash value for each token
        token_hash = int(compute_hash_value(token), 16)

        # # Reduce its length to be 'hasbits' bits long
        # token_hash = token_hash & ((1 << hashbits) - 1)  # commented out since md5 is 128bits binary, and thus we don't need masking.

        # For each bit, add or subtract weight
        # Set the weight to 1 for all tokens
        # TODO: Set weight based on token frequency  
        weight = 1
        for i in range(hashbits): 
            bitmask = weight << i 
            if token_hash & bitmask: 
                vector[i] += 1
            else: 
                vector[i] -= 1

    simhash_value = 0
    for i in range(hashbits): 
        if vector[i] >= 0: 
            simhash_value |= (1 << i)
   
    return simhash_value


def distance(hash1: int, hash2: int) -> int: 
    return bin(hash1 ^ hash2).count('1')


