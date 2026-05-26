"""
Domain validation utilities (CNPJ, CPF, etc.)
"""


def validate_cnpj(cnpj: str) -> bool:
    """
    Validate a Brazilian CNPJ using the official check-digit algorithm.

    Accepts raw (digits only) or formatted (XX.XXX.XXX/XXXX-XX) strings.
    Returns False for all-same-digit CNPJs (e.g. "00000000000000") regardless
    of computed check digits, as these are explicitly invalid per Receita Federal.
    """
    digits = "".join(c for c in cnpj if c.isdigit())

    if len(digits) != 14:
        return False

    # All-same-digit CNPJs are invalid (e.g. 11111111111111)
    if len(set(digits)) == 1:
        return False

    def _check(d: list[int], weights: list[int]) -> int:
        remainder = sum(x * w for x, w in zip(d, weights)) % 11
        return 0 if remainder < 2 else 11 - remainder

    nums = [int(c) for c in digits]

    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    if _check(nums[:12], w1) != nums[12]:
        return False

    w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    if _check(nums[:13], w2) != nums[13]:
        return False

    return True
