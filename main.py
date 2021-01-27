import pickle
import sys
from enum import Enum
from typing import TextIO

import praw
import requests
from praw import Reddit
from praw.models.comment_forest import CommentForest
from praw.models.listing.mixins.redditor import SubListing
from praw.reddit import Subreddit, Submission, Comment, Redditor

from datetime import datetime
from datetime import timedelta

import urllib.request
from bs4 import BeautifulSoup


class Link:
    def __init__(self, link, expires):
        self.link: str = link
        self.expires: datetime = expires

    def __str__(self):
        return "[link: " + self.link + ", expires: " + str(self.expires) + "]"


class Thread:
    def __init__(self, expires):
        self.std_set: set = set()
        self.expires: datetime = expires

    def __str__(self):
        return "[id: " + str(self.std_set) + ", expires: " + str(self.expires) + "]"


class UserSetting(Enum):
    top = 1
    none = 2


link_expiration_delta: timedelta = timedelta(days=1)
thread_expiration_delta: timedelta = timedelta(weeks=1)
sub: str = "cpp_questions"
# sub: str = "test"

link_cache: dict = dict()
thread_cache: dict = dict()
user_settings: dict = dict()
current_thread_id: str

reddit: Reddit = praw.Reddit(client_id="XXX",
                             client_secret="XXX",
                             user_agent="XXX",
                             username="XXX",
                             password="XXX")


def __log(log_line: str):
    print(log_line)

    now: datetime = datetime.now()
    file_name: str = "std_bot_log_{}_{}_{}.txt".format(now.year, now.month, now.day)
    file: TextIO = open(file_name.encode("ascii", "ignore"), "a")
    file.write(log_line)
    file.close()


def send_bot(message: str):
    token: str = "XXX"
    url: str = f'https://api.telegram.org/bot{token}/sendMessage'
    data = {'chat_id': 111, 'text': message}
    requests.post(url, data).json()


def log(message: str):
    log_line: str = "{}:\n\t{}\n".format(datetime.now(), "\n\t".join(message.splitlines()))
    __log(log_line)


def log_skip():
    log_line: str = "\n\n===== ===== ===== ===== ===== ===== ===== ===== ===== ===== ===== ===== ===== ===== =====\n\n"
    __log(log_line)


def check_cache_for_expiration(cache: dict):
    to_remove: list = []
    for key in cache:
        if cache[key].expires < datetime.now():
            to_remove.append(key)

    for key in to_remove:
        log("Removing expired cache entry ({}: {})".format(key, cache[key]))
        cache.pop(key, None)


def save_obj(obj, name):
    with open('obj/' + name + '.pkl', 'wb+') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


def load_obj(name):
    with open('obj/' + name + '.pkl', 'rb') as f:
        return pickle.load(f)


# ++++++++++ indexing ++++++++++


def get_sub_comments(comment, comments_list):
    comments_list.append(comment)
    if not hasattr(comment, "replies"):
        replies = comment.comments()
    else:
        replies = comment.replies
    for child in replies:
        get_sub_comments(child, comments_list)


def get_all(submission_id) -> list:
    submission: Submission = reddit.submission(submission_id)
    comments: CommentForest = submission.comments
    comments_list: list = list()
    comment: Comment
    for comment in comments:
        get_sub_comments(comment, comments_list)
    return comments_list


def index_line(line: str):
    if line.startswith(">") or line.startswith("    "):
        return

    line = line.lower()

    token_start_pos: int = line.find("[")
    while token_start_pos != -1:
        token_end_pos: int = line.find("]", token_start_pos)
        if token_end_pos == -1:
            token_start_pos = line.find("[", token_start_pos + 1)
            continue

        token: str = line[token_start_pos + 1: token_end_pos]

        link_start_pos: int = line.find("(", token_end_pos)
        if link_start_pos == -1:
            token_start_pos = line.find("[", token_end_pos + 1)
            continue

        link_end_pos: int = line.find(")", link_start_pos)
        if link_end_pos == -1:
            token_start_pos = line.find("[", link_start_pos + 1)
            continue

        log("indexing linked ({})".format(token))
        thread_cache[current_thread_id].std_set.add(token.strip())
        token_start_pos = line.find("[", link_end_pos + 1)


def index_comment(comment):
    line: str
    for line in comment.body.splitlines():
        line = line.replace("\\_", "_")
        index_line(line)


def index(comment):
    if current_thread_id in thread_cache:
        log("indexing new comment")
        index_comment(comment)
    else:
        log("indexing unknown thread")
        thread_cache[current_thread_id] = Thread(expires=datetime.now() + thread_expiration_delta)
        comment_list: list = get_all(current_thread_id)
        for comment in comment_list:
            index_comment(comment)

    save_obj(thread_cache, "thread_cache")


# ---------- indexing ----------

# ++++++++++ comment parsing ++++++++++


def parse_line(line: str) -> set:
    std_set: set = set()

    if line.startswith(">") or line.startswith("    "):
        return std_set

    line: str = line.lower()

    pos_start: int = line.find("std::")
    while pos_start != -1:
        pos_end: int = pos_start + 5

        while pos_end < len(line):
            if line[pos_end].isalnum():
                pos_end += 1
            elif line[pos_end] == "_":
                pos_end += 1
            elif (line[pos_end] == ":") and (pos_end + 1 < len(line)) and (line[pos_end + 1] == ":"):
                pos_end += 2
            else:
                break

        if pos_end <= len(line):
            std: str = line[pos_start:pos_end].strip()
            if len(std) > 5:
                std_set.add(std)

        pos_start = line.find("std::", pos_end)

    return std_set


def parse_body(body) -> set:
    std_set: set = set()
    line: str
    for line in body.splitlines():
        line = line.replace("\\_", "_")
        result: set = parse_line(line)
        std_set.update(result)

    return std_set


# ---------- comment parsing ----------

# ++++++++++ online search ++++++++++


def search_online(std: str) -> str:
    url_base: str = 'https://en.cppreference.com'

    search_std: str = std.replace("::", "%3A%3A")
    url: str = url_base + "/mwiki/index.php?title=Special%3ASearch&search=" + search_std
    with urllib.request.urlopen(url) as response:
        soup = BeautifulSoup(response.read(), "html.parser")

        content = soup.find("title").contents[0]
        if not str(content).startswith("Search results for"):
            log("found std ({}) in a direct hit".format(std))
            return response.url  # Direct hit!

        search_results = soup.find_all("div", attrs={"class": "mw-search-result-heading"})

        if len(search_results) == 0:
            log("found no result for std ({})".format(std))
            return ""  # No result

        for result in search_results:
            link = result.find("a")
            content = link.contents
            if (len(content) > 0) and (content[0] == std):
                log("found std ({}) in a matching result".format(std))
                return url_base + link.get("href")  # Matching result

        log("found no direct match for std ({}), returning first link".format(std))
        return url_base + search_results[0].find("a").get("href")  # No match, return first result


def find_link(std: str) -> Link:
    log("searching for std ({})".format(std))
    if std in link_cache:
        log("found std ({}) in cache".format(std))
        return link_cache[std]

    log("std ({}) not cached, searching online".format(std))
    link: Link = Link(link=search_online(std), expires=datetime.now() + link_expiration_delta)
    link_cache[std] = link
    return link


# ---------- online search ----------


def reply_with_links(comment, forced: bool):
    check_cache_for_expiration(link_cache)
    check_cache_for_expiration(thread_cache)
    index(comment)

    std_set: set = parse_body(comment.body)
    log("stds found: {}".format(", ".join(std_set)))

    unlinked_stds: set = std_set - thread_cache[current_thread_id].std_set

    if len(unlinked_stds) == 0 and not forced:
        log("no unlinked stds found")
        return

    log("caching new linked stds: {}".format(", ".join(unlinked_stds)))
    thread_cache[current_thread_id].std_set.update(unlinked_stds)
    save_obj(thread_cache, "thread_cache")

    link_list: list = []
    for std in std_set:
        _link: str = find_link(std).link
        if len(_link) > 0:
            link_list.append("[{}]({})".format(std, _link))

    if len(link_list) == 0:
        log("no std link")
        return

    manual_link: str = "[readme](https://github.com/Narase33/std_bot/blob/main/README.md)"
    message: str = "I found the following unlinked functions/types in your comment and linked them:"
    message += "  \n" + ", ".join(link_list)
    message += "\n\n---"
    message += "\n\n^(Please let me know what you think about me. I'm version 0.2.2, last update: 26.01.21)"
    message += "  \n^(Recent changes: Only responding to top comments. Added commands to interact with me.)"
    message += " " + manual_link

    log(message)

    save_obj(thread_cache, "thread_cache")
    save_obj(link_cache, "link_cache")

    bot_message: str = f'https://www.reddit.com{comment.permalink}\n{", ".join(std_set)}'
    if forced:
        bot_message += "\nforced"

    send_bot(bot_message)
    comment.reply(message)


def has_comment(body: str) -> str:
    for line in body.splitlines():
        line = line.replace("\\_", "_").strip("*_")

        if line.startswith("!std"):
            return line

    return ""


def process_comment(comment):
    if comment.author == "std_bot":
        return

    if comment.link_author == "[deleted]":
        return

    body: str = comment.body

    log_skip()
    comment_link: str = f"https://www.reddit.com{comment.permalink}"
    log(f"{comment_link}\n{body}\n\n----- ----- ----- ----- -----\n")

    parent = comment.parent()
    author = comment.author

    command: str = has_comment(body)

    if command == "!std":
        reply_with_links(comment, True)
    elif command == "!std ignore_me":
        if isinstance(parent, Comment) and (parent.author == "std_bot"):
            log(f"user {author} will be ignored from now on")
            user_settings[author] = UserSetting.none
            save_obj(user_settings, "user_settings")
            send_bot(f"{author} will be ignored from now on")
    elif command == "!std follow_me":
        if isinstance(parent, Comment) and (parent.author == "std_bot") and (author in user_settings):
            log(f"user {author} will be followed again")
            user_settings[author] = UserSetting.top
            save_obj(user_settings, "user_settings")
            send_bot(f"{author} will be followed again")
    elif comment.is_root:
        if (author in user_settings) and (user_settings[author] == UserSetting.none):
            log("user marked as 'none', ignoring comment")
        else:
            reply_with_links(comment, False)
    else:
        log("Comment is neither top comment, nor enforced or command. Ignored")


def statistics():
    redditor: Redditor = reddit.redditor('std_bot')
    comments: SubListing = redditor.comments

    score: int = 0
    count: int = 0
    for comment in comments.new():
        score += comment.score
        count += 1

    log(f"Count: {count}")
    log(f"Score: {score}")
    log(f"Average: {score / count}")
    log_skip()


def start():
    send_bot("Checking connection")
    statistics()

    global thread_cache
    thread_cache = load_obj("thread_cache")

    global link_cache
    link_cache = load_obj("link_cache")

    global user_settings
    user_settings = load_obj("user_settings")

    subreddit: Subreddit = reddit.subreddit(sub)
    for comment in subreddit.stream.comments(skip_existing=True):  # skip_existing=True
        try:
            global current_thread_id
            current_thread_id = comment.submission.id
            process_comment(comment)
        except:
            log("error during process!\nComment:\n{}\n\nError:\n{}"
                .format(comment.body, sys.exc_info()[0]))


if __name__ == '__main__':
    try:
        start()
    except:
        log("something went really wrong!\nError:\n{}".format(sys.exc_info()[0]))
