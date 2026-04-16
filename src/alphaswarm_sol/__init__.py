"""AlphaSwarm.sol - AI-native smart contract security analysis."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("alphaswarm-sol")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"
