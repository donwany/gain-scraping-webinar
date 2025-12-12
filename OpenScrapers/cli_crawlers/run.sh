#!/bin/bash

# Basic crawl4ai with markdown output
crwl https://www.myjoyonline.com/news/ -o markdown --output-file ./data/myjoyonline.json

crwl https://citinewsroom.com/news/ -o markdown --output-file data/citinewsroom.md

crwl https://www.ghanaweb.com/GhanaHomePage/NewsArchive/ -o markdown --output-file data/ghanaweb.json

crwl https://3news.com/category/news/ -o markdown --output-file data/3news.json

crwl https://en.wikipedia.org/wiki/List_of_large_language_models -o markdown --output-file data/wikipedia.md 


### Docling
docling https://arxiv.org/pdf/2206.01062 --to md
docling --from html https://www.myjoyonline.com/news/ --to md
docling --from html https://thinkingmachines.ai/blog/lora/ --to md
docling --from html https://presidency.gov.gh/members-of-the-cabinet --to md
docling --from html https://en.wikipedia.org/wiki/List_of_large_language_models --to md