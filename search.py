#!/usr/bin/python
import re
import nltk
import sys
import getopt
import codecs
import struct
import math
import io
import collections
import timeit

RECORD_TIME = False # toggling for recording the time taken for indexer
BYTE_SIZE = 4       # docID is in int

"""
conducts boolean queries from queries_file and writes outputs to output_file
params:
    dictionary_file:    dictionary file produced by indexer
    postings_file:      postings file produced by indexer
    queries_file:       file of boolean queries
    output_file:        responses to boolean queries
"""
def search(dictionary_file, postings_file, queries_file, output_file):
    # open files
    dict_file = codecs.open(dictionary_file, encoding='utf-8')
    post_file = io.open(postings_file, 'rb')
    query_file = codecs.open(queries_file, encoding='utf-8')
    out_file = open(output_file, 'w')

    # load dictionary to memory
    loaded_dict = load_dictionary(dict_file)
    dictionary = loaded_dict[0]     # dictionary map
    indexed_docIDs = loaded_dict[1] # list of all docIDs indexed in sorted order
    dict_file.close()

    # process each query
    queries_list = query_file.read().splitlines()
    for i in range(len(queries_list)):
        query = queries_list[i]
        result = process_query(query, dictionary, post_file, indexed_docIDs)
        # write each result to output
        for j in range(len(result)):
            docID = str(result[j])
            if (j != len(result) - 1):
                docID += ' '
            out_file.write(docID)
        if (i != len(queries_list) - 1):
            out_file.write('\n')

    # close files
    post_file.close()
    query_file.close()
    out_file.close()

"""
returns 2-tuple of loaded dictionary and total df
params:
    dict_file: opened dictionary file
"""
def load_dictionary(dict_file):
    dictionary = {}                 # dictionary map loaded
    indexed_docIDs = []             # list of all docIDs indexed
    docIDs_processed = False        # if indexed_docIDs is processed

    # load each term along with its df and postings file pointer to dictionary
    for entry in dict_file.read().split('\n'):
        # if entry is not empty (last line in dictionary file is empty)
        if (entry):
            # if first line of dictionary, process list of docIDs indexed
            if (not docIDs_processed):
                indexed_docIDs = [int(docID) for docID in entry[20:-1].split(',')]
                docIDs_processed = True
            # else if dictionary terms and their attributes
            else:
                token = entry.split(" ")
                term = token[0]
                df = int(token[1])
                offset = int(token[2])
                dictionary[term] = (df, offset)

    return (dictionary, indexed_docIDs)

"""
returns the list of docIDs in the result for the given query
params:
    query:          the query string e.g. 'bill OR Gates AND (vista OR XP) AND NOT mac'
    dictionary:     the dictionary in memory
    indexed_docIDs: the list of all docIDs indexed (used for negations)

"""
def process_query(query, dictionary, post_file, indexed_docIDs):
    stemmer = nltk.stem.porter.PorterStemmer() # instantiate stemmer
    # prepare query list
    query = query.replace('(', '( ')
    query = query.replace(')', ' )')
    query = query.split(' ')

    results_stack = []
    postfix_queue = collections.deque(shunting_yard(query)) # get query in postfix notation as a queue

    while postfix_queue:
        token = postfix_queue.popleft()
        result = [] # the evaluated result at each stage
        # if operand, add postings list for term to results stack
        if (token != 'AND' and token != 'OR' and token != 'NOT'):
            token = stemmer.stem(token) # stem the token
            # default empty list if not in dictionary
            if (token in dictionary): 
                result = load_posting_list(post_file, dictionary[token][0], dictionary[token][1])
        
        # else if AND operator
        elif (token == 'AND'):
            right_operand = results_stack.pop()
            left_operand = results_stack.pop()
            # print(left_operand, 'AND', left_operand) # check
            result = boolean_AND(left_operand, right_operand)   # evaluate AND

        # else if OR operator
        elif (token == 'OR'):
            right_operand = results_stack.pop()
            left_operand = results_stack.pop()
            # print(left_operand, 'OR', left_operand) # check
            result = boolean_OR(left_operand, right_operand)    # evaluate OR

        # else if NOT operator
        elif (token == 'NOT'):
            right_operand = results_stack.pop()
            # print('NOT', right_operand) # check
            result = boolean_NOT(right_operand, indexed_docIDs) # evaluate NOT

        # push evaluated result back to stack
        results_stack.append(result)                        
        # print ('result', result) # check

    # NOTE: at this point results_stack should only have one item and it is the final result
    if len(results_stack) != 1: print ("ERROR: results_stack. Please check valid query") # check for errors
    
    return results_stack.pop()

"""
returns posting list for term corresponding to the given offset
params:
    post_file:  opened postings file
    length:     length of posting list (same as df for the term)
    offset:     byte offset which acts as pointer to start of posting list in postings file
"""
def load_posting_list(post_file, length, offset):
    post_file.seek(offset)
    posting_list = []
    for i in range(length):
        posting = post_file.read(BYTE_SIZE)
        docID = struct.unpack('I', posting)[0]
        posting_list.append(docID)
    return posting_list

"""
returns the list of postfix tokens converted from the given infix expression
params:
    infix_tokens: list of tokens in original query of infix notation
"""
def shunting_yard(infix_tokens):
    # define precedences
    precedence = {}
    precedence['NOT'] = 3
    precedence['AND'] = 2
    precedence['OR'] = 1
    precedence['('] = 0
    precedence[')'] = 0    

    # declare data strucures
    output = []
    operator_stack = []

    # while there are tokens to be read
    for token in infix_tokens:
        
        # if left bracket
        if (token == '('):
            operator_stack.append(token)
        
        # if right bracket, pop all operators from operator stack onto output until we hit left bracket
        elif (token == ')'):
            operator = operator_stack.pop()
            while operator != '(':
                output.append(operator)
                operator = operator_stack.pop()
        
        # if operator, pop operators from operator stack to queue if they are of higher precedence
        elif (token in precedence):
            # if operator stack is not empty
            if (operator_stack):
                current_operator = operator_stack[-1]
                while (operator_stack and precedence[current_operator] > precedence[token]):
                    output.append(operator_stack.pop())
                    if (operator_stack):
                        current_operator = operator_stack[-1]

            operator_stack.append(token) # add token to stack
        
        # else if operands, add to output list
        else:
            output.append(token.lower())

    # while there are still operators on the stack, pop them into the queue
    while (operator_stack):
        output.append(operator_stack.pop())
    # print ('postfix:', output)  # check
    return output

"""
returns the list of docIDs which is the compliment of given right_operand 
params:
    right_operand:  sorted list of docIDs to be complimented
    indexed_docIDs: sorted list of all docIDs indexed
"""
def boolean_NOT(right_operand, indexed_docIDs):
    # complement of an empty list is list of all indexed docIDs
    if (not right_operand):
        return indexed_docIDs
    
    result = []
    r_index = 0 # index for right operand
    for item in indexed_docIDs:
        # if item do not match that in right_operand, it belongs to compliment 
        if (item != right_operand[r_index]):
            result.append(item)
        # else if item matches and r_index still can progress, advance it by 1
        elif (r_index + 1 < len(right_operand)):
            r_index += 1
    return result

"""
returns list of docIDs that results from 'OR' operation between left and right operands
params:
    left_operand:   docID list on the left
    right_operand:  docID list on the right
"""
def boolean_OR(left_operand, right_operand):
    result = []     # union of left and right operand
    l_index = 0     # current index in left_operand
    r_index = 0     # current index in right_operand

    # while lists have not yet been covered
    while (l_index < len(left_operand) or r_index < len(right_operand)):
        # if both list are not yet exhausted
        if (l_index < len(left_operand) and r_index < len(right_operand)):
            l_item = left_operand[l_index]  # current item in left_operand
            r_item = right_operand[r_index] # current item in right_operand
            
            # case 1: if items are equal, add either one to result and advance both pointers
            if (l_item == r_item):
                result.append(l_item)
                l_index += 1
                r_index += 1

            # case 2: l_item greater than r_item, add r_item and advance r_index
            elif (l_item > r_item):
                result.append(r_item)
                r_index += 1

            # case 3: l_item lower than r_item, add l_item and advance l_index
            else:
                result.append(l_item)
                l_index += 1

        # if left_operand list is exhausted, append r_item and advance r_index
        elif (l_index >= len(left_operand)):
            r_item = right_operand[r_index]
            result.append(r_item)
            r_index += 1

        # else if right_operand list is exhausted, append l_item and advance l_index 
        else:
            l_item = left_operand[l_index]
            result.append(l_item)
            l_index += 1

    return result

"""
returns list of docIDs that results from 'AND' operation between left and right operands
params:
    left_operand:   docID list on the left
    right_operand:  docID list on the right
"""
def boolean_AND(left_operand, right_operand):
    # perform 'merge'
    result = []                                 # results list to be returned
    l_index = 0                                 # current index in left_operand
    r_index = 0                                 # current index in right_operand
    l_skip = int(math.sqrt(len(left_operand)))  # skip pointer distance for l_index
    r_skip = int(math.sqrt(len(right_operand))) # skip pointer distance for r_index

    while (l_index < len(left_operand) and r_index < len(right_operand)):
        l_item = left_operand[l_index]  # current item in left_operand
        r_item = right_operand[r_index] # current item in right_operand
        
        # case 1: if match
        if (l_item == r_item):
            result.append(l_item)   # add to results
            l_index += 1            # advance left index
            r_index += 1            # advance right index
        
        # case 2: if left item is more than right item
        elif (l_item > r_item):
            # if r_index can be skipped (if new r_index is still within range and resulting item is <= left item)
            if (r_index + r_skip < len(right_operand)) and right_operand[r_index + r_skip] <= l_item:
                r_index += r_skip
            # else advance r_index by 1
            else:
                r_index += 1

        # case 3: if left item is less than right item
        else:
            # if l_index can be skipped (if new l_index is still within range and resulting item is <= right item)
            if (l_index + l_skip < len(left_operand)) and left_operand[l_index + l_skip] <= r_item:
                l_index += l_skip
            # else advance l_index by 1
            else:
                l_index += 1

    return result

"""
prints the proper command usage
"""
def print_usage():
    print ("usage: " + sys.argv[0] + " -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results")

dictionary_file = postings_file = queries_file = output_file = None
try:
    opts, args = getopt.getopt(sys.argv[1:], 'd:p:q:o:')
except (getopt.GetoptError, err):
    usage()
    sys.exit(2)
for o, a in opts:
    if o == '-d':
        dictionary_file = a
    elif o == '-p':
        postings_file = a
    elif o == '-q':
        queries_file = a
    elif o == '-o':
        output_file = a
    else:
        assert False, "unhandled option"
if (dictionary_file == None or postings_file == None or queries_file == None or output_file == None):
    print_usage()
    sys.exit(2)

if (RECORD_TIME): start = timeit.default_timer()                    # start time
search(dictionary_file, postings_file, queries_file, output_file)   # call the search engine on queries
if (RECORD_TIME): stop = timeit.default_timer()                     # stop time
if (RECORD_TIME): print ('Querying time:' + str(stop - start))      # print time taken