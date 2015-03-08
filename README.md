# Boolean Retrieval Engine
This is a Python implementation of indexing and searching techniques for Boolean retrieval. A Boolean query contains the  operators `AND`, `OR`, `NOT`, `(`, and `)`. This is a good [source](http://nlp.stanford.edu/IR-book/html/htmledition/boolean-retrieval-1.html) for more information on Boolean retrieval and its techniques.
## Requirements
* [NLTK](http://www.nltk.org/) installed
* Corpus for indexing and searching with constituent documents named numerically (e.g. Reuters corpus in NLTK data)

## Indexing
`$ python index.py -i <directory-of-documents> -d <dictionary-file> -p <postings-file>`
* `<directory-of-documents>` is the directory for the collection of documents to be indexed
* `<dictionary-file>` is the filename of dictionary to be created by indexer
  * Human readeable
  * First line contains metadata of metainformation and indicates all docIDs indexed in ascending order: e.g. "Indexed from docIDs:1,5,6,9,10,11,12,13,14,18,19,22,23,24,27,29,30,36,37,..."
  * Subsequent lines are of the format: "\<term\> \<df\> \<byte offset in postings file\>"
* `<postings-file>` is the filename of the postings file created by indexer
 * Non-human readable
 * raw bytes where every 4 bytes represents a docID int

## Searching
`$ python search.py -d <dictionary-file> -p <postings-file> -q <file-of-queries> -o <output-file-of-results>`
* `<dictionary-file>` and `<postings-file>` are created by the indexer as aforementioned
* `<file-of-queries>` is a text file containing the list of Boolean queries, one for each line
 * A Boolean query is a space-delimited boolean expression of search terms. E.g. `term1 OR term2 AND (term3 OR term4) AND NOT term5`
 * Boolean operators must be given in UPPERCASE
* `<output-file-of-results>` is the name of the output file for the search results for the given queries
 * For the same line number, each line in `<output-file-of-results>` is a space-delimited list of docIDs (sorted ascending) corresponding to the search result for the corresponding query in `<file-of-queries>`
