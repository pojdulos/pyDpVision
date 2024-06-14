# __init__.py

from .parserATMDL import ParserATMDL
from .parserDICOM import ParserDICOM
from .parserIMAGE2D import ParserIMAGE2D
from .parserNRRD import ParserNRRD
from .parserOBJ import ParserOBJ
from .parserSTL import ParserSTL

__all__ = [
	"ParserATMDL",
	"ParserDICOM",
	"ParserIMAGE2D",
	"ParserNRRD",
	"ParserOBJ",
	"ParserSTL"
	]
