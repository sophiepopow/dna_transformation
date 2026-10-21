import os
import random
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import dna_codec

MAPPING = {'00': 'A', '01': 'T', '10': 'C', '11': 'G'}


def test_dna_codec_roundtrip():
    random.seed(0)
    for _ in range(100):
        length = random.randint(1, 10_000)
        data = random.randbytes(length)
        bits = dna_codec.bytes_to_bits(data)
        assert dna_codec.bits_to_bytes(bits) == data
        dna = dna_codec.bits_to_dna(bits, MAPPING)
        assert dna_codec.dna_to_bits(dna, MAPPING) == bits
