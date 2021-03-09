import urllib.request
from typing import Optional

from bs4 import BeautifulSoup, Tag


def get_alpha_numeric_substring(s: str) -> str:
    s2: str = ""
    for c in s:
        if c.isalnum() or (c == "_"):
            s2 += c
        else:
            break
    return s2


def get_link(link: Tag, inner_tag: str, token: str) -> Optional[str]:
    tag: Tag = link.find(inner_tag)
    if (tag is not None) and (get_alpha_numeric_substring(tag.contents[0]) == token):
        return link.get("href")


def search_online_std_symbol_index(std: str) -> Optional[str]:
    url_base: str = 'https://en.cppreference.com'

    subtoken_list: list = std.replace("%3A%3A", "::").split("::")

    url: str = url_base + "/w/cpp/symbol_index"

    for index in range(1, len(subtoken_list)):
        with urllib.request.urlopen(url) as response:
            soup: BeautifulSoup = BeautifulSoup(response.read(), "html.parser")

            link: Tag
            for link in soup.find_all("a"):
                if index == (len(subtoken_list) - 1):
                    hit: str = get_link(link, "tt", subtoken_list[index])
                    if hit is not None:
                        return url_base + hit

                    namespace: str = get_link(link, "code", subtoken_list[index])
                    if namespace is not None:
                        return url_base + namespace
                else:
                    next_link: str = get_link(link, "code", subtoken_list[index])
                    if next_link is not None:
                        url = url_base + next_link
                        break
            return None


def search_online_std_search(std: str) -> Optional[str]:
    url_base: str = 'https://en.cppreference.com'

    search_std: str = std.replace("::", "%3A%3A")
    url: str = url_base + "/mwiki/index.php?title=Special%3ASearch&search=" + search_std
    with urllib.request.urlopen(url) as response:
        soup = BeautifulSoup(response.read(), "html.parser")

        content = soup.find("title").contents[0]
        if not str(content).startswith("Search results for"):
            return response.url  # Direct hit!

        search_results = soup.find_all("div", attrs={"class": "mw-search-result-heading"})
        for result in search_results:
            link = result.find("a")
            content = link.contents
            if (len(content) > 0) and (content[0] == std):
                return url_base + link.get("href")  # Matching result


def search_online_std(std: str) -> Optional[str]:
    index_result: str = search_online_std_symbol_index(std)
    if index_result is not None:
        return index_result
    return search_online_std_search(std)
