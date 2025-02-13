from bs4 import BeautifulSoup
from tokenizer import Tokenize, ComputeTokenFrequencies
import hashlib

def compute_hash_value(content: str) -> str:
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def compute_simhash(text, hashbits = 64): 
    """
    """
    # create a list of tokens(words) in the html text
    # and compute the frequence of each token
    tokens = Tokenize(text)
    token_freq_table = {}
    ComputeTokenFrequencies(tokens, token_freq_table)  # token_freq_table updated as {token: freq}

    # initialize all hashbits to 0
    vector = [0] * hashbits

    for token in tokens:

        # compute a hash for each token
        # reduce its length to be 'hasbits' bits long
        token_hash = int(compute_hash_value(token), 16)
        token_hash = token_hash & ((1 << hashbits) - 1)

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

def distance(hash1, hash2): 
    return bin(hash1 ^ hash2).count('1')


