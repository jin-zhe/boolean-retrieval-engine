#!/usr/bin/python
import re
import nltk
import sys
import getopt
import codecs
import os
import struct
import timeit

LIMIT = None                # (for testing) to limit the number of documents indexed
IGNORE_STOPWORDS = True     # toggling the option for ignoring stopwords
IGNORE_NUMBERS = True       # toggling the option for ignoring numbers
IGNORE_SINGLES = True       # toggling the option for ignoring single character tokens
RECORD_TIME = False         # toggling for recording the time taken for indexer
BYTE_SIZE = 4               # docID is in int

"""
indexer which produces dictionary and postings file
params:
    document_directory: corpus directory for indexing
    dictionary_file:    dictionary of terms
    postings_file:      postings file for all terms in dictionary
"""
def index(document_directory, dictionary_file, postings_file):
    # preprocess docID list
    docID_list = [int(docID_string) for docID_string in os.listdir(document_directory)]
    docID_list.sort()

    stemmer = nltk.stem.porter.PorterStemmer()
    stopwords = nltk.corpus.stopwords.words('english')
    docs_indexed = 0    # counter for the number of docs indexed
    dictionary = {}     # key: term, value: [postings list]

    # for each document in corpus
    for docID in docID_list:
        if (LIMIT and docs_indexed == LIMIT): break
        file_path = os.path.join(document_directory, str(docID))
        
        # if valid document
        if (os.path.isfile(file_path)):
            file = codecs.open(file_path, encoding='utf-8')
            document = file.read()                  # read entire document
            tokens = nltk.word_tokenize(document)   # list of word tokens from document
            
            # for each term in document
            for word in tokens:
                term = word.lower()         # casefolding
                if (IGNORE_STOPWORDS and term in stopwords):    continue    # if ignoring stopwords
                if (IGNORE_NUMBERS and is_number(term)):        continue    # if ignoring numbers
                term = stemmer.stem(term)   # stemming
                if (term[-1] == "'"):
                    term = term[:-1]        # remove apostrophe
                if (IGNORE_SINGLES and len(term) == 1):         continue    # if ignoring single terms
                
                # if term not already in dictionary
                if (term not in dictionary):
                    dictionary[term] = [docID]   # define new term in in dictionary
                # else if term is already in dictionary
                else:
                    # if current docID is not yet in the postings list for term, append it
                    if (dictionary[term][-1] != docID):
                        dictionary[term].append(docID)
                    
            docs_indexed += 1
            file.close()

    # open files for writing   
    dict_file = codecs.open(dictionary_file, 'w', encoding='utf-8')
    post_file = open(postings_file, 'wb')

    byte_offset = 0 # byte offset for pointers to postings file

    # write list of docIDs indexed to first line of dictionary
    dict_file.write('Indexed from docIDs:')
    for i in range(docs_indexed):
        dict_file.write(str(docID_list[i]) + ',')
    dict_file.write('\n')

    # build dictionary file and postings file
    for term, postings_list in dictionary.items():
        df = len(postings_list)                     # document frequency is the same as length of postings list
        
        # write each posting into postings file
        for docID in postings_list:
            posting = struct.pack('I', docID)   # pack docID into a byte array of size 4
            post_file.write(posting)

        # write to dictionary file and update byte offset
        dict_file.write(term + " " + str(df) + " " + str(byte_offset) + "\n")
        byte_offset += BYTE_SIZE * df

    # close files
    dict_file.close()
    post_file.close()

"""
This function is modified from: http://stackoverflow.com/questions/354038/how-do-i-check-if-a-string-is-a-number-in-python
returns True if the token is a number else false
param:
    token:  token string
"""
def is_number(token):
    token = token.replace(",", "")  # ignore commas in token
    # tries if token can be parsed as float
    try:
        float(token)
        return True
    except ValueError:
        return False

"""
prints the proper command usage
"""
def print_usage():
    print ("usage: " + sys.argv[0] + " -i directory-of-documents -d dictionary-file -p postings-file")

document_directory = dictionary_file = postings_file = None
try:
    opts, args = getopt.getopt(sys.argv[1:], 'i:d:p:')

# if illegal arguments, print usage to user and exit
except (getopt.GetoptError, err):
    print_usage()
    sys.exit(2)

# for each option parsed
for o, a in opts:
    if o == '-i':
        document_directory = a
    elif o == '-d':
        dictionary_file = a
    elif o == '-p':
        postings_file = a
    else:
        assert False, "unhandled option"

# if missing out on an argument, print usage to user and exit
if document_directory == None or dictionary_file == None or postings_file == None:
    print_usage()
    sys.exit(2)

if (RECORD_TIME): start = timeit.default_timer()                              # start time
index(document_directory, dictionary_file, postings_file)   # call the indexer
if (RECORD_TIME): stop = timeit.default_timer()                               # stop time
if (RECORD_TIME): print ('Indexing time:' + str(stop - start))                # print time taken