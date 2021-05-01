import traceback
import urllib.request

import pickle5 as pickle
# import pickle as pickle

import sys
from enum import Enum
from time import sleep
from typing import TextIO

import praw
import requests
from praw import Reddit
from praw.models.comment_forest import CommentForest
from praw.models.listing.mixins.redditor import SubListing
from praw.reddit import Subreddit, Submission, Comment, Redditor

from datetime import datetime
from datetime import timedelta

from prawcore import ServerError

from search_online_std import search_online_std


class Link:
    def __init__(self, link, expires):
        self.link: str = link
        self.expires: datetime = expires

    def __str__(self):
        return "[link: " + (self.link or "[None]") + ", expires: " + str(self.expires) + "]"


class Thread:
    def __init__(self, expires):
        self.std_set: set = set()
        self.expires: datetime = expires

    def __str__(self):
        return "[id: " + str(self.std_set) + ", expires: " + str(self.expires) + "]"


class UserSetting(Enum):
    top = 1
    none = 2


link_expiration_delta: timedelta = timedelta(weeks=1)
thread_expiration_delta: timedelta = timedelta(weeks=1)
signature: str = "\n\n---\n\n^(Last update: 01.05.21. Last change: Free links considered) [readme](https://github.com/Narase33/std_bot/blob/main/README.md)"
sub: str = "cpp_questions"
# sub: str = "test"

link_cache: dict = dict()
thread_cache: dict = dict()
user_settings: dict = dict()
current_thread_id: str

reddit: Reddit


def __log(log_line: str):
    print(log_line)

    try:
        now: datetime = datetime.now()
        file_name: str = "std_bot_log_{}_{}_{}.txt".format(now.year, now.month, now.day)
        file: TextIO = open(file_name, "a", encoding="utf-8")
        file.write(log_line)
        file.close()
    except UnicodeError as error:
        print(error)


def send_bot(message: str):
    token: str = "1546898859:AAFHlRL4qUNFHFdZqcpGTt7KNZHlzlFdTLE"
    url: str = f'https://api.telegram.org/bot{token}/sendMessage'
    data = {'chat_id': 606500329, 'text': message}
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


def get_all_comments_from_submission(submission: Submission) -> list:
    comments: CommentForest = submission.comments
    comments_list: list = list()
    comment: Comment
    for comment in comments:
        get_sub_comments(comment, comments_list)
    return comments_list


def index_op_line(line: str):
    std_set: set = find_stds_in_line(line)
    for std in std_set:
        log("indexing OP use of ({})".format(std))
        thread_cache[current_thread_id].std_set.add(std)


def index_line(line: str):
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
        thread_cache[current_thread_id].std_set.add(token.strip().strip("`"))
        token_start_pos = line.find("[", link_end_pos + 1)


def index_op(submission: Submission):
    line: str
    for line in submission.selftext.splitlines():
        if line.startswith(">"):
            continue

        line = line.replace("\\_", "_")
        index_op_line(line)


def index_free_link_line(line: str) -> set:
    links: set = set()

    token_start_pos: int = line.find("http")
    while token_start_pos != -1:
        token_end_pos: int = line.find(" ", token_start_pos + 1)
        if token_end_pos != -1:
            links.add(line[token_start_pos: token_end_pos+1])
            token_start_pos = line.find("http", token_end_pos)
        else:
            links.add(line[token_start_pos:])
            return links

    return links


def index_free_links(comment: Comment) -> set:
    links: set = set()

    line: str
    for line in comment.body.splitlines():
        if line.startswith(">") or line.startswith("    ") or line.startswith("\t"):
            continue

        line = line.replace("\\_", "_")
        links.update(index_free_link_line(line))

    return links


def index_user_comment(comment: Comment):
    line: str
    for line in comment.body.splitlines():
        if line.startswith(">") or line.startswith("    ") or line.startswith("\t"):
            continue

        line = line.replace("\\_", "_")
        index_line(line)


def index(comment):
    if current_thread_id in thread_cache:
        log("indexing new comment")
        index_user_comment(comment)
    else:
        log("indexing unknown thread")
        thread_cache[current_thread_id] = Thread(expires=datetime.now() + thread_expiration_delta)

        submission: Submission = reddit.submission(current_thread_id)
        index_op(submission)
        comment_list: list = get_all_comments_from_submission(submission)
        for comment in comment_list:
            index_user_comment(comment)

    save_obj(thread_cache, "thread_cache")


# ---------- indexing ----------

# ++++++++++ comment parsing ++++++++++


def find_stds_in_line(line: str) -> set:
    std_set: set = set()

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

        if line.startswith(">") or line.startswith("    ") or line.startswith("\t"):
            continue

        result: set = find_stds_in_line(line)
        std_set.update(result)

    return std_set

# ---------- comment parsing ----------


def find_link_for_single_std(std: str) -> str:
    log("searching for std ({})".format(std))
    if std in link_cache:
        log("found std ({}) in cache".format(std))
        link: str = link_cache[std].link

        if link is not None:
            return link

    log("std ({}) not cached, searching online".format(std))

    hyperlink: str = search_online_std(std)
    if hyperlink is None:
        log(f"Couldn't find a link for {std}")
        send_bot(f"Couldn't find a link for {std}")

    link_cache[std] = Link(link=hyperlink, expires=datetime.now() + link_expiration_delta)
    return hyperlink


def cache_unlinked_stds(unlinked_stds: set):
    log("caching new linked stds: {}".format(", ".join(unlinked_stds)))
    thread_cache[current_thread_id].std_set.update(unlinked_stds)

    save_obj(thread_cache, "thread_cache")
    save_obj(link_cache, "link_cache")


def find_links_for_std_list(std_set: set) -> list:
    link_list: list = list()
    for std in std_set:
        _link: str = find_link_for_single_std(std)
        if (_link is not None) and (len(_link) > 0):
            link_list.append((std, _link))
    return link_list


def reply_with_links(comment, forced: bool):
    check_cache_for_expiration(link_cache)
    check_cache_for_expiration(thread_cache)

    # Get every STD
    std_set: set = parse_body(comment.body)
    if len(std_set) == 0:
        log(f'no stds found')
        return

    log(f'stds found: {", ".join(std_set)}')

    # Removing cached STDs
    unlinked_stds: set = std_set - thread_cache[current_thread_id].std_set
    if (len(unlinked_stds)) == 0 and not forced:
        log("every std already linked")
        return

    cache_unlinked_stds(unlinked_stds)

    # Getting links for every STD
    link_list: list = find_links_for_std_list(std_set)
    if len(link_list) == 0:
        log("no std links found")
        return

    # Removing free links
    free_links: set = index_free_links(comment)
    for free_link in free_links:
        for online_link in link_list:
            if free_link == online_link[1]:
                link_list.remove(online_link)

    if len(link_list) == 0:
        log("no std links found")
        return

    # Add STDs and links together
    link_list_transformed: list = list()
    for std_link in link_list:
        link_list_transformed.append("[{}]({})".format(std_link[0], std_link[1]))

    message: str = f'Unlinked STL entries: {", ".join(link_list_transformed)}' + signature

    bot_message: str = f'https://www.reddit.com{comment.permalink}\n{", ".join(std_set)}'
    if forced:
        bot_message += "\nforced"

    log(message)
    send_bot(bot_message)
    comment.reply(message)


def has_command(body: str) -> str:
    for line in body.splitlines():
        line = line.replace("\\_", "_").strip("*_")

        if line.startswith("!std"):
            return line

    return ""


def message_to_bot(comment) -> bool:
    bot_message: str = f'https://www.reddit.com{comment.permalink}\nMessage to me:\n{comment.body}'
    send_bot(bot_message)

    command: str = has_command(comment.body)
    if command == "!std ignore_me":
        log(f"user {comment.author} will be ignored from now on")
        user_settings[comment.author] = UserSetting.none
        save_obj(user_settings, "user_settings")
        return True
    elif command == "!std follow_me":
        log(f"user {comment.author} will be followed again")
        user_settings[comment.author] = UserSetting.top
        save_obj(user_settings, "user_settings")
        return True

    return False


def process_comment(comment):
    if comment.author == "std_bot":
        return

    body: str = comment.body

    log_skip()

    comment_link: str = f"({comment.id}) https://www.reddit.com{comment.permalink}"
    log(f"{comment_link}\n{body}\n\n----- ----- ----- ----- -----\n")

    index(comment)

    if isinstance(comment.parent(), Comment) and (comment.parent().author == "std_bot"):
        if message_to_bot(comment):
            return

    forced: bool = has_command(comment.body).startswith("!std")
    if comment.is_root:
        if (comment.author in user_settings) and (user_settings[comment.author] == UserSetting.none):
            log("user marked as 'none', ignoring comment")
        else:
            reply_with_links(comment, forced)
    elif forced:
        reply_with_links(comment, True)
    else:
        log("Comment is neither top comment nor enforced. Ignored")


def statistics():
    redditor: Redditor = reddit.redditor('std_bot')
    comments: SubListing = redditor.comments

    score: int = 0
    count: int = 0
    for comment in comments.new():
        score += comment.score
        count += 1

    log_skip()
    log(f"Count: {count}"
        f"\nScore: {score}"
        f"\nAverage: {score / count}")


def load_storages():
    global thread_cache
    thread_cache = load_obj("thread_cache")

    global link_cache
    link_cache = load_obj("link_cache")

    global user_settings
    user_settings = load_obj("user_settings")


def debug_comment():
    _id: str = "gvx475e"

    comment = reddit.comment(_id)

    global current_thread_id
    current_thread_id = comment.submission.id

    global thread_cache
    if current_thread_id in thread_cache:
        thread_cache.pop(current_thread_id)

    process_comment(comment)


def start():
    global reddit
    reddit = praw.Reddit(client_id="XXXX",
                         client_secret="XXXX",
                         user_agent="XXXX",
                         username="std_bot",
                         password="XXXX")

    send_bot("bot starting")

    statistics()

    load_storages()
    # debug_comment()

    subreddit: Subreddit = reddit.subreddit(sub)
    for comment in subreddit.stream.comments(skip_existing=True):  # skip_existing=True
        try:
            global current_thread_id
            current_thread_id = comment.submission.id
            process_comment(comment)
        except ServerError as error:
            log(str(error))
            send_bot(f"server error:\n{str(error)}")
            sleep(60)
        except Exception as e2:
            trace2: str = f"\n{e2}\n{traceback.format_exc()}"
            log(f"error during process!\nComment:\n{comment.body}\n\nError:\n{sys.exc_info()[0]}{trace2}")
            send_bot(f"error during process: {comment.submission.id}{trace2}")
            sleep(60)


def can_connect(host='http://google.com'):
    try:
        urllib.request.urlopen(host)
        return True
    except:
        return False


if __name__ == '__main__':
    while True:
        try:
            if can_connect():
                start()
            else:
                sleep(60)
                send_bot("could not connect to internet")
        except Exception as e:
            trace: str = f"\n{e}\n{traceback.format_exc()}"
            log(f"something went really wrong!\nError:\n{sys.exc_info()[0]}{trace}")
            send_bot(f"really bad error.{trace}")
            sleep(60)
