import sys
import os
import re
from enum import Enum

"""
Script takes one text file as an argument and outputs the frequencies words in the file.
Output results in format: 
    <token> - <freq>
Run script from the command line. Must include a path to a text file in command line argument
    Usage: python PartA.py <file_path>
"""

class LexState(Enum):
    LS_START        = 0
    LS_ALPHANUM     = 1
    LS_STOP         = 2

def is_alphanum_char(char: str) -> bool: 
    """
    Uses regular expression to test if a string with a single char
    is  alphanumerical.

    Args:
        char (str): Single character

    Returns: 
        bool: True if char is alphanumerical.

    Runtime Complexity:
        O(1), process a single character
    """
    assert len(char) > 0 and len(char) < 2, "Input char parameter should be string of length 1."
        
    return bool(re.match(r'[a-zA-Z0-9]', char))

def Tokenize(line_content: str) -> list[str]:
    """
    Reads in a line of string text and returns a dictionary mapping token(key) to frequency of token in text(value).
    A token is a sequence of alphanumeric characters, independent of capitalization (so Apple, apple, aPpLe are the same token)

    Allowed to use regular expressions

    Args:
        line_content (str): A string containing a single line of text content read from input file.

    Returns:
        list[str]: list of tokens in line

    Runtime Complexity: 
        O(n) where n is the number of characters in the string line_content. 
        Each character is processed once.
    """
    token_list = []

    index = 0
    while index < len(line_content):
        start_index = index
        end_index = index
        state = LexState.LS_START

        while state != LexState.LS_STOP:

            #check that interating index does not 
            #raise out-of-range exceptation when accessing file_content 
            if not (index < len(line_content)):
                state = LexState.LS_STOP
                end_index = index
                continue

            #get chacter current index to advance state machine
            c = line_content[index]

            # switch states
            if state == LexState.LS_START:              #Start State
                if is_alphanum_char(c):
                    state = LexState.LS_ALPHANUM
                else:
                    state = LexState.LS_STOP
            elif state == LexState.LS_ALPHANUM:          #AlphaNum State
                end_index = index
                if is_alphanum_char(c):
                    state = LexState.LS_ALPHANUM
                else:
                    state = LexState.LS_STOP
            else:
                raise Exception("Error: Tokenization state machine reached an invalid state.")
            #END: if-else 
            index += 1
        #END: While

        # add token to list only if it is a non-empty string
        token = line_content[start_index : end_index] #(start_index, end_index]
        if len(token) > 0:
            token_list.append(token.lower())
    #END: While

    return token_list

def ComputeTokenFrequencies(token_list: list[str], token_frequency: dict[str,int]):
    """
    Takes a list of tokens and updates the values of frequency table.

    Args:
        token_list (list[str]) : A list of tokens
        token_frequency (dict[str,int]) : A dictionary which maps tokens to their frequency of appearence.
    
    Returns:
        token_frequency (dict[str,int]) : Updated token-frequency table returned through "token_frequency" parameter
    
    Runtime Complexity: 
        O(n), where n is the number of tokens in token_list.
        Each token is processed once.
    """
    for token in token_list:
        if token in token_frequency:
            #if token already in dictionary increment count
            token_frequency[token] += 1
        else:
            #add word to dictionary and set value to 1
            token_frequency[token] = 1

def PrintTokenFrequency(token_frequency: dict[str, int]):
    """
    Prints out the word frequency count onto the screen. 
    The printout is ordered by non-increasing frequency. 
    (so, the highest frequency words first; order in the cases of ties is alphabetically).

    Args:
        dict[str, int]: Dictionary mapping tokens to frequency value.
    
    Runtime Complexity: 
        O(n log n), where n is the number of unique tokens.
        Sorting dominates the complexity.
    
    """
    #sort the frequencies in descending order. Time Complexity: O(nlogn)
    key_value_pairs = token_frequency.items()
    sorted_pairs = sorted(key_value_pairs, key=lambda pair: (-pair[1], pair[0]), reverse=False)

    # Time Complexity - O(n)
    for token,frequncy in sorted_pairs:
        print(f"{token} - {frequncy}")

# TODO: Add a brief runtime complexity explanation on top of each method or function
def TokenizeTextFile(file_path: str) -> dict[str, int]:
    """
    Takes in a file path to a .txt document and returns a dictionary 
    mapping string tokens to the frequency of token in .txt file

    Args:
        filepath (str): path to a txt document

    Returns:
        dict[str, int]: key: Token string value: Frequency of token in .txt file
    
    Time Complexity: 
        O(n), where n is the total number of characters in the file.
        Each character must be processed once during tokenization
    """

    if os.path.splitext(file_path)[1].lower() != ".txt":
        print(f"Error: Invalid file type. Usage: python PartA.py <file_path>/<file_name>.txt")
        sys.exit(1)

    token_frequency = {}

    try:
        with open(file_path, 'r', encoding="utf-8", errors="ignore") as file:
            # Read line of text file
            for line in file:
                ComputeTokenFrequencies(Tokenize(line), token_frequency)
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
        sys.exit(1)

    return token_frequency

# Entry point
if __name__ == "__main__":
    #  Check if the file path is provided
    if len(sys.argv) != 2:
        print("Error: Incorrect number of arguments. Usage: python PartA.py <file_path>/<file_name>.txt")
        sys.exit(1)

    # Get the file path from the command line
    file_path = sys.argv[1]

    # Read in text file
    token_frequency = TokenizeTextFile(file_path)

    PrintTokenFrequency(token_frequency)