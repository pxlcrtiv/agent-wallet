"""Token amounts: one place where raw units become numbers you can read.

An ERC-20 amount is an integer in the token's own units.  Turning it into
a number a human can act on needs the token's ``decimals`` — a chain
fact, never a constant.  :class:`TokenAmount` carries the raw value, the
scale and the symbol together, so no caller has to remember the
conversion and no caller can quietly assume a fixed number of decimals.

The module depends on nothing but the standard library: it is the single
source of truth for "what is this raw amount worth".
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TokenAmount:
    """A raw ERC-20 amount together with the token's scale and symbol.

    ``decimals`` is the token's own scale — always read from the chain,
    never hardcoded.  ``human`` and ``display`` are the only two ways a
    raw amount should be rendered.
    """

    raw: int
    decimals: int
    symbol: str

    @property
    def human(self) -> float:
        """The amount in token units (1000.0 for 1000 USDC)."""
        return self.raw / 10**self.decimals

    @property
    def display(self) -> str:
        """The amount formatted for prose ("1000.0000 USDC")."""
        return "%.4f %s" % (self.human, self.symbol)

    def with_human(self, human: float) -> TokenAmount:
        """The same token, carrying an amount expressed in token units."""
        return TokenAmount(
            raw=int(human * 10**self.decimals),
            decimals=self.decimals,
            symbol=self.symbol,
        )
