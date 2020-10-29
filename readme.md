# Pageminer
Python scraper that scrapes specific tags from a website. Crawls to links within the main page and repeats the process 
n number of times as specified in the input.

## Input format 
The script accepts a json file with input in this sample format:
```json
{"depth": "<Crawling depth in int>",
  "scrapeSameDomain": "<Boolean to filter links with a different domain>",
  "saveFileDir": "Directory/to/save",
  "HTMLElementList": ["title", "script:src", "div", "p", "a:href", "label"],
  "runURL": [
              {"ID": "6961",
               "URL": "http://www.samplesite1.com"},
              {"ID": "6962", 
               "URL": "http://www.samplesite2.com"}],
  "pstrings": "priority,strings,here"}
```
## Additional helper scripts 
### Splitinput.py
Splits a large input file into multiple files in preparation for running scraper with multiple instances
### init_instances.py
Runs multiple instances of pageminer.py with a for each entry on the target directory.
Used in tandem with splitinput.py to enable multitasking to deal with a large number of inputs
