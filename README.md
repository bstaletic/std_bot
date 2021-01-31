# std_bot

## What does the bot do?
std_bot searches in r/cpp_questions for STL related stuff (everything "std::\*", calling this "*token*" from now on) and tries to link them with the reference page from [cppreference.com](https://en.cppreference.com/w/)

Be aware that the bot is still in development. Every behaviour is subject to change

If the feedback is mostly negative and I can't get it to work without annoying the users in the sub, I will deactivate it

I also beg to consider that this is the first program I've ever written in Python. If you think it sucks, give me feedback.

## What comments does it respond to and how?

std_bot responds only to top comments or comments that have "**!std**" at the beginning of any line

Tokens in quotes (start with ">") or code blocks (start with "    ", 4 spaces) will be ignored

Also if a comment only contains tokens that have been linked previously in other comments (by the bot or any other user) it will be ignored. You can use "**!std**" to enforce linking (but not after editing as the bot only sees new comments)

## How does the bot get it's results?

The bot starts a search on cppreference.com

- If the search results in a direct hit, the link is used
- If the search doesn't have a direct hit, the first result is used
- If the search doesn't give anything, the token is ignored

## How can I give feedback or suggestions?

I'm very grateful for every form of feedback, positive or negative.

You can give feedback under every comment std_bot makes or write private messages.

## I don't want the bot to respond to my comments

Just reply with "**!std ignore_me**" to any bot comment and it will ignore your comments from now on

Type "**!std follow_me**" to let it follow you again

Even if ignored you can still use "**!std**" to manually invoke the bot

## I'm still annoyed by the bot

I'm sorry to hear that. Best you can do is to give me some feedback and ignore the bot via Reddit

## ToDo

- [x] Searching with https://en.cppreference.com/w/cpp/symbol_index instead of using their search function for more and better results
- [ ] ~~Adding other popular frameworks (like boost::)~~
  - [ ] Probably not possible due to missing search function and symbol index
- [ ] Recognizing used links even if they're not bound to the token
- [ ] Tokens used by OP should be added to index as OP probably knows about them
  - [ ] This should also work if OP uses the 'using' expression (as "std::" normally indicates STL tokens)


## TL:DR commands

| Command        | Result                                      |
| -------------- | ------------------------------------------- |
| !std           | Enforce link creation                       |
| !std ignore_me | The bot will ignore you ("!std" will works) |
| !std follow_me | The bot will follow you again               |

