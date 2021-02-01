# std_bot

## What does the bot do?
std_bot searches in r/cpp_questions for STL related stuff (everything "std::\*", calling this "*token*" from now on) and tries to link them with the reference page from [cppreference.com](https://en.cppreference.com/w/)

Be aware that the bot is still in development. Every behaviour is subject to change

If the feedback is mostly negative and I can't get it to work without annoying the users in the sub, I will deactivate it

I also beg to consider that this is the first program I've ever written in Python. If you think it sucks, give me feedback.

## What comments does it respond to and how?

A simplified flow control:

![Picture](https://github.com/Narase33/std_bot/blob/main/ControlFlow.bmp)

## How does the bot get it's results?

The bot uses https://en.cppreference.com/w/cpp/symbol_index to look for the symbols. Nested symbols like std::chrono::Monday result in multiple requests:

- -> https://en.cppreference.com/w/cpp/symbol_index

- -> https://en.cppreference.com/w/cpp/symbol_index/chrono

- -> https://en.cppreference.com/w/cpp/chrono/weekday

## How can I give feedback or suggestions?

I'm very grateful for every form of feedback, positive or negative.

You can give feedback under every comment std_bot makes or write private messages.

## I don't want the bot to respond to my comments

Just reply with "**!std ignore_me**" to any bot comment and it will ignore your comments from now on

Type "**!std follow_me**" to let it follow you again

Even if ignored you can still use "**!std**" to manually invoke the bot

Please do not use any markdown symbols. The commands are only recognized if there is nothing else in the specific line

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

