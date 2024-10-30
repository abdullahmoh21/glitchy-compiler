import sys
from enum import Enum
class Token:
    def __init__(self, type, value):
        self.type = type      # type of the token
        self.value = value    # value of the token
    
    # Returns a string representation of the keyword or null if it's not a keyword.
    @staticmethod
    def checkIfKeyword(tokenText):
        for type in TokenType:
            # keyword enum values are 1XX.
            if type.name.lower() == tokenText and 100 <= type.value < 200:
                return type
        return None
    
    @staticmethod
    def checkIfLogicalOperator(tokenText):
        for type in TokenType:
            if type.name.lower() == tokenText and 400 <= type.value < 500:
                return type
        return None

# TokenType is our enum for all the types of tokens.
class TokenType(Enum):
    ERROR = -2
    EOF = -1
    NEWLINE = 0
    INTEGER = 1
    BOOLEAN = 2
    IDENTIFIER = 3
    STRING = 4
    NULL = 5
    DOUBLE = 6
    # Punctuation.
    LBRACE = 7      # {
    RBRACE = 8      # }
    LPAREN = 9      # (
    RPAREN = 10     # )
    SEMICOLON = 11  # ;
    COMMA = 12      # ,
    DOT = 13        # .
    COLON = 14      # :
    QMARK = 15      # ?
    # -------------------------------- #
    # Keywords.
    WHILE = 101
    FUNCTION = 102
    SET = 103  
    IF = 104
    ELSE = 105
    ELIF = 106
    FOR = 107
    RETURN = 108
    BREAK = 109
    # -------------------------------- #
    # Operators.
    EQ = 301            # =
    PLUS = 302          # +
    MINUS = 303         # -    
    ASTERISK = 304      # *
    SLASH = 305         # /
    MODUlO = 306        # %
    POW = 307           # ^
    EQEQ = 308          # ==
    NOTEQ = 309         # !=
    LT = 310            # <
    LTEQ = 311          # <=
    GT = 312            # >
    GTEQ = 313          # >=
    INCREMENT = 314     # ++ 
    DECREMENT = 315     # --
    PLUS_EQUAL = 316    # +=
    MINUS_EQUAL = 317   # -=
    # -------------------------------- #
    # Logical operators.
    AND = 401       # &&
    OR = 402        # ||
    NOT = 403       # !
    