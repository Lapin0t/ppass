#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""Markov's own password generator, approved by Shannon.

Passwords are generated based on a markovian model of a word corpus. If the
corpus contains prononceable words, generated words will probably be
prononceable too. The password will be sequence of words generated by the
model joined by a configurable separator. One special character is added after
each word. Words will be added until the target entropy is reached. Models are
stored in ~/.local/share/andrei.

To generate a model you can give a 

Usage:
  andrei --help
  andrei [--clip] [--entropy N] [--model NAME] [--min-word-len X]
         [--max-word-len Y] [--specials SPECIALS] [--sep SEP]
  andrei modelize [--filter=REGEX] STATE_SIZE NAME FILE...

Options:
  -h, --help             show this help message
  -c, --clip             copy the password to the clipboard instead of printing it
  -e N, --entropy=N      minimum entropy for the password [default: 50]
  -m NAME, --model=NAME  model used for generation [default: latin_3]
  --min-word-len=X       discard words shorter than X [default: 5]
  --max-word-len=Y       discard words longer than Y [default: 10]
  --specials=SPECIALS    special characters to put after each word [default: 0123456789!@#$%^&*?+=]
  --sep=SEP              word separator [default: -]
  --filter=REGEX         regex used to filter words in the corpus [default: \\b(\w+)\\b]

Note:
  Python's `os.urandom` is used as a secure randomness source. If it is
  unavailable, a warning will be emitted and it will fall back to python's
  default random generator (Mersenne Twister). In the later case you SHOULD NOT
  use the generated password for security purpose. In any case, USE AT YOUR OWN
  RISK. See https://docs.python.org/3.5/library/os.html#os.urandom for more
  info.
"""


from bisect import bisect
from collections import namedtuple
from itertools import accumulate
from math import log, ceil
from os import path
import pickle
import random
import re

from docopt import docopt
import logbook


_sysrand = random.SystemRandom()
try:
    _sysrand.randrange(10)
except NotImplementedError:
    logbook.warning('could not find a reliable randomness source: DO NOT USE '
          'IT FOR SECURITY PURPOSE')
    randrange = random.randrange
else:
    randrange = _sysrand.randrange


def word_list(files, filter=r'\b([a-zA-Z]+)\b'):
    pat = re.compile(filter)
    words = []
    for f in files:
        with open(f) as s:
            words.extend(pat.findall(s.read()))
    return words #[w.lower() for w in words]


def count_transitions(words, n):
    trans = {}
    for w in words:
        xs = '\x00'*n + w + '\x01'
        for i in range(len(w)+1):
            curr = xs[i:i+n]
            succ = xs[i+n]
            if curr not in trans:
                trans[curr] = {succ: 1}
            elif succ not in trans[curr]:
                trans[curr][succ] = 1
            else:
                trans[curr][succ] += 1
    return trans


Node = namedtuple('Node', ('choices', 'cumdist', 'entropy'))


def build_model(trans):
    model = {}
    for (state, succs) in trans.items():
        tot = sum(succs.values())
        ord = tuple(succs.items())  # get some fixed order
        model[state] = Node(
            choices=tuple(x[0] for x in ord),
            cumdist=tuple(accumulate([x[1] for x in ord])),
            entropy=-sum(f/tot * log(f/tot) for f in succs.values()))
    return model


class Generator:
    def __init__(self, words=None, state_size=None, path=None):
        if path is not None:
            with open(path, 'rb') as s:
                self.state_size, self.model = pickle.load(s)
        else:
            assert words is not None and state_size is not None, 'bad arguments'
            self.state_size = state_size
            trans = count_transitions(words, state_size)
            self.model = build_model(trans)

    def dump_model(self, path):
        with open(path, 'wb') as s:
            pickle.dump((self.state_size, self.model), s)

    def generate(self):
        state = '\x00' * self.state_size
        out = []
        entropy = 0
        while True:
            node = self.model[state]
            entropy += node.entropy
            r = randrange(node.cumdist[-1])
            succ = node.choices[bisect(node.cumdist, r)]
            if succ == '\x01':
                return ''.join(out), entropy
            out.append(succ)
            state = state[1:] + succ

    def generate_password(self, min_entropy, min_word_len=5, max_word_len=10,
            specials='0123456789!@#$%^&*?+=~', sep='-'):
        words = []
        entropy = 0
        n = len(specials)
        sp_ent = log(n, 2) if n > 0 else 0
        while entropy < min_entropy:
            while True:
                w, e = self.generate()
                if min_word_len <= len(w) < max_word_len:
                    break
            entropy += e
            if n > 0:
                s = specials[randrange(n)]
                entropy += sp_ent
                words.append(w + s)
            else:
                words.append(w)
        return (sep.join(words), entropy)

def main():
    logbook.StderrHandler(format_string='{record.level_name}: {record.message}').push_application()

    args = docopt(__doc__)
    BASE = path.expanduser(path.join('~', '.local', 'share', 'andrei'))
    if args['modelize']:
        words = word_list(args['FILE'], args['--filter'])
        gen = Generator(words, int(args['STATE_SIZE']))
        gen.dump_model(path.join(BASE, args['NAME']))
        print('Sucessfully generated model {}'.format(args['NAME']))
    else:
        gen = Generator(path=path.join(BASE, args['--model']))
        pw, ent = gen.generate_password(
            int(args['--entropy']),
            int(args['--min-word-len']),
            int(args['--max-word-len']),
            args['--specials'],
            args['--sep'])
        if args['--clip']:
            pass
        else:
            logbook.info('entropy: {:.3f}'.format(ent))
            print(pw)

if __name__ == '__main__':
    main()
