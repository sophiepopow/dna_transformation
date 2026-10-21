def bytes_to_bits(data: bytes) -> str:
    return ''.join(f'{b:08b}' for b in data)


def bits_to_dna(bits: str, mapping: dict[str, str]) -> str:
    if len(bits) % 2 != 0:
        raise ValueError('bits length must be a multiple of 2')
    return ''.join(mapping[bits[i:i + 2]] for i in range(0, len(bits), 2))


def dna_to_bits(dna: str, mapping: dict[str, str]) -> str:
    inverse = {value: key for key, value in mapping.items()}
    try:
        return ''.join(inverse[nucleotide] for nucleotide in dna)
    except KeyError as exc:
        raise ValueError(f'Invalid DNA character: {exc.args[0]}') from exc


def bits_to_bytes(bits: str) -> bytes:
    if len(bits) % 8 != 0:
        raise ValueError('bits length must be a multiple of 8')
    return bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))
