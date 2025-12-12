# # from langchain_compat import ensure_langchain_compat
# # ensure_langchain_compat()
# from scrapegraphai.graphs import SmartScraperGraph
# import json


# # Define the configuration for the scraping pipeline
# graph_config = {
#     "llm": {
#         "model": "ollama/llama3.1",
#         "model_tokens": 8192
#     },
#     "verbose": True,
#     "headless": False,
# }

# # Create the SmartScraperGraph instance
# smart_scraper_graph = SmartScraperGraph(
#     prompt="Extract useful information from the webpage, including a description of what the company does, founders and social media links",
#     source="https://scrapegraphai.com/",
#     config=graph_config
# )

# if __name__ == '__main__':
#     # Run the pipeline
#     result = smart_scraper_graph.run()
#     print(json.dumps(result, indent=4))