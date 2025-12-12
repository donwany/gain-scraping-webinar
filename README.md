## Install - Python3.13.3
```bash

curl -LsSf https://astral.sh/uv/install.sh | sh
# or
brew install uv

uv init
uv venv
source .venv/bin/activate # macOS

uv pip install -r requirements.txt
# or 
uv sync
```
## API Keys
 - Get your API key from: https://www.firecrawl.dev/app/api-keys
 - Get your API key from: https://platform.openai.com/api-keys

## Related Tools & Libraries

- **ScrapeGraphAI** — https://github.com/ScrapeGraphAI/Scrapegraph-ai.git  
- **FireCrawl** — https://github.com/firecrawl/firecrawl.git  
- **Crawl4AI** — https://github.com/unclecode/crawl4ai.git  
- **Docling** — https://docling-project.github.io/docling/


## Basic crawl4ai with markdown output
```bash

crwl https://www.myjoyonline.com/news/ -o markdown --output-file myjoyonline.json
crwl https://citinewsroom.com/news/ -o markdown --output-file citinewsroom.md

crwl https://www.ghanaweb.com/GhanaHomePage/NewsArchive/ -o markdown --output-file ghanaweb.json
crwl https://3news.com/category/news/ -o markdown --output-file 3news.json 

```

## Docling
```bash

docling https://arxiv.org/pdf/2206.01062 --to md
docling --from html https://www.myjoyonline.com/news/ --to md
docling --from html https://thinkingmachines.ai/blog/lora/ --to md
docling --from html https://presidency.gov.gh/members-of-the-cabinet --to md
```

### Application of WebScraping
 - Research
 - ML/AI model training
 - Earn Income
 - Bloggers in Ghana
 - Unlimited Possibilities