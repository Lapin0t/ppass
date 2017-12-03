from itertools import accumulate
from random import randrange
from bisect import bisect
from math import log
from collections import namedtuple
import pickle


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

    def generate(self, rand=randrange):
        state = '\x00' * self.state_size
        out = []
        entropy = 0
        while True:
            node = self.model[state]
            entropy += node.entropy
            r = rand(node.cumdist[-1])
            succ = node.choices[bisect(node.cumdist, r)]
            if succ == '\x01':
                return ''.join(out), entropy
            out.append(succ)
            state = state[1:] + succ


if __name__ == '__main__':
    with open('words.txt') as s:
        words = [w.strip().lower() for w in s.readlines()]
