import newspaper
from newspaper import Article
from skill_manager import Skill
import requests
from bs4 import BeautifulSoup

class WebResearcher(Skill):
    name = "Web Researcher"
    description = "Scrapes and summarizes news or web content from URLs or topics."
    keywords = ["summarize", "research", "news", "article", "topic"]
    supported_intents = ["researcher_skill"]

    # List of free sources for general topic research
    FREE_SOURCES = [
        "https://www.bbc.com/news",
        "https://techcrunch.com",
        "https://en.wikipedia.org/wiki/Main_Page"
    ]

    def run(self, parameters: dict):
        user_input = parameters.get("user_input", "").strip()
        text = user_input.lower()

        # === 1. RESEARCH A SPECIFIC URL ===
        if "http" in text:
            url = [word for word in text.split() if "http" in word][0]
            try:
                article = Article(url)
                article.download()
                article.parse()
                article.nlp()  # summary & keywords

                response = f"### 📰 Summary: {article.title}\n"
                response += f"> {article.summary[:500]}...\n\n"
                response += f"**Key Points:** {', '.join(article.keywords[:5])}"
                return response
            except Exception as e:
                return f"I couldn't reach that site. Error: {e}"

        # === 2. GENERAL TOPIC RESEARCH ===
        results = []
        for site_url in self.FREE_SOURCES:
            try:
                paper = newspaper.build(site_url, memoize_articles=False)
                matched_articles = []

                for article in paper.articles[:5]:  # check first 5 articles per source
                    article.download()
                    article.parse()
                    title_text = f"{article.title} {article.text}".lower()
                    if text in title_text:
                        matched_articles.append(
                            f"**{article.title}**\n> {article.text[:300]}..."
                        )

                if matched_articles:
                    results.append(f"### Results from {site_url}:\n" + "\n\n".join(matched_articles))

            except Exception as e:
                results.append(f"Could not access {site_url}. Error: {e}")

        # === 3. FALLBACK ===
        if not results:
            return "I couldn't find exact matches. Try providing a specific URL or slightly different topic."

        return "\n\n".join(results)
