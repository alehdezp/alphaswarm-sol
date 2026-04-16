"""VQL 2.0 Lexer - Tokenization with error recovery and fuzzy matching."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class TokenType(Enum):
    """Token types for VQL 2.0."""

    # Keywords
    DESCRIBE = auto()
    FIND = auto()
    MATCH = auto()
    FLOW = auto()
    PATTERN = auto()
    WHERE = auto()
    RETURN = auto()
    WITH = auto()
    AS = auto()
    FROM = auto()
    TO = auto()
    THROUGH = auto()
    REQUIRE = auto()
    EXCLUDE = auto()
    SOURCES = auto()
    SINKS = auto()
    PATHS = auto()
    LIMIT = auto()
    OFFSET = auto()
    ORDER = auto()
    BY = auto()
    GROUP = auto()
    HAVING = auto()
    UNION = auto()
    INTERSECT = auto()
    EXCEPT = auto()
    OPTIONAL = auto()
    EXISTS = auto()
    IN = auto()
    NOT = auto()
    AND = auto()
    OR = auto()
    CASE = auto()
    WHEN = auto()
    THEN = auto()
    ELSE = auto()
    END = auto()
    LENS = auto()
    SEVERITY = auto()
    FORWARD = auto()
    BACKWARD = auto()
    ANY = auto()
    ALL = auto()
    TAINTED = auto()
    UNSAFE = auto()
    FUNCTIONS = auto()
    INFLUENCERS = auto()
    ASC = auto()
    DESC = auto()
    DISTINCT = auto()

    # Options
    COMPACT = auto()
    EXPLAIN = auto()
    NO = auto()
    EVIDENCE = auto()
    VERBOSE = auto()

    # Introspection
    TYPES = auto()
    PROPERTIES = auto()
    FOR = auto()
    EDGES = auto()
    PATTERNS = auto()
    LENSES = auto()
    SCHEMA = auto()

    # Operators
    EQ = auto()  # =
    NEQ = auto()  # !=
    GT = auto()  # >
    LT = auto()  # <
    GTE = auto()  # >=
    LTE = auto()  # <=
    REGEX = auto()
    LIKE = auto()
    CONTAINS = auto()
    CONTAINS_ANY = auto()
    CONTAINS_ALL = auto()

    # Aggregations
    COUNT = auto()
    SUM = auto()
    AVG = auto()
    MAX = auto()
    MIN = auto()
    COLLECT = auto()
    LENGTH = auto()
    NODES = auto()

    # Delimiters
    LPAREN = auto()  # (
    RPAREN = auto()  # )
    LBRACKET = auto()  # [
    RBRACKET = auto()  # ]
    LBRACE = auto()  # {
    RBRACE = auto()  # }
    COMMA = auto()  # ,
    DOT = auto()  # .
    COLON = auto()  # :
    SEMICOLON = auto()  # ;
    ARROW_RIGHT = auto()  # ->
    ARROW_LEFT = auto()  # <-
    DASH = auto()  # -
    STAR = auto()  # *
    PLUS = auto()  # +
    MINUS = auto()  # - (arithmetic)
    SLASH = auto()  # /
    PERCENT = auto()  # %
    DOTDOT = auto()  # ..

    # Literals
    IDENTIFIER = auto()
    STRING = auto()
    INTEGER = auto()
    FLOAT = auto()
    BOOLEAN = auto()
    NULL = auto()

    # Special
    EOF = auto()
    NEWLINE = auto()
    COMMENT = auto()


@dataclass
class Token:
    """A lexical token."""

    type: TokenType
    value: Any
    line: int
    column: int
    raw_text: str = ""

    def __str__(self) -> str:
        if self.value != self.type.name:
            return f"{self.type.name}({self.value})"
        return self.type.name


class LexerError(Exception):
    """Lexer error with position information."""

    def __init__(self, message: str, line: int, column: int, hint: str | None = None):
        self.message = message
        self.line = line
        self.column = column
        self.hint = hint
        super().__init__(f"Line {line}, column {column}: {message}")


KEYWORDS = {
    "DESCRIBE": TokenType.DESCRIBE,
    "FIND": TokenType.FIND,
    "SELECT": TokenType.FIND,  # Alias
    "SHOW": TokenType.FIND,  # Alias
    "MATCH": TokenType.MATCH,
    "FLOW": TokenType.FLOW,
    "PATTERN": TokenType.PATTERN,
    "WHERE": TokenType.WHERE,
    "RETURN": TokenType.RETURN,
    "WITH": TokenType.WITH,
    "AS": TokenType.AS,
    "FROM": TokenType.FROM,
    "TO": TokenType.TO,
    "THROUGH": TokenType.THROUGH,
    "REQUIRE": TokenType.REQUIRE,
    "EXCLUDE": TokenType.EXCLUDE,
    "SOURCES": TokenType.SOURCES,
    "SINKS": TokenType.SINKS,
    "PATHS": TokenType.PATHS,
    "LIMIT": TokenType.LIMIT,
    "OFFSET": TokenType.OFFSET,
    "ORDER": TokenType.ORDER,
    "BY": TokenType.BY,
    "GROUP": TokenType.GROUP,
    "HAVING": TokenType.HAVING,
    "UNION": TokenType.UNION,
    "INTERSECT": TokenType.INTERSECT,
    "EXCEPT": TokenType.EXCEPT,
    "OPTIONAL": TokenType.OPTIONAL,
    "EXISTS": TokenType.EXISTS,
    "IN": TokenType.IN,
    "NOT": TokenType.NOT,
    "AND": TokenType.AND,
    "OR": TokenType.OR,
    "CASE": TokenType.CASE,
    "WHEN": TokenType.WHEN,
    "THEN": TokenType.THEN,
    "ELSE": TokenType.ELSE,
    "END": TokenType.END,
    "LENS": TokenType.LENS,
    "SEVERITY": TokenType.SEVERITY,
    "FORWARD": TokenType.FORWARD,
    "BACKWARD": TokenType.BACKWARD,
    "ANY": TokenType.ANY,
    "ALL": TokenType.ALL,
    "TAINTED": TokenType.TAINTED,
    "UNSAFE": TokenType.UNSAFE,
    "FUNCTIONS": TokenType.FUNCTIONS,
    "INFLUENCERS": TokenType.INFLUENCERS,
    "ASC": TokenType.ASC,
    "DESC": TokenType.DESC,
    "DISTINCT": TokenType.DISTINCT,
    "COMPACT": TokenType.COMPACT,
    "EXPLAIN": TokenType.EXPLAIN,
    "NO": TokenType.NO,
    "EVIDENCE": TokenType.EVIDENCE,
    "VERBOSE": TokenType.VERBOSE,
    "TYPES": TokenType.TYPES,
    "PROPERTIES": TokenType.PROPERTIES,
    "FOR": TokenType.FOR,
    "EDGES": TokenType.EDGES,
    "PATTERNS": TokenType.PATTERNS,
    "LENSES": TokenType.LENSES,
    "SCHEMA": TokenType.SCHEMA,
    "REGEX": TokenType.REGEX,
    "LIKE": TokenType.LIKE,
    "CONTAINS": TokenType.CONTAINS,
    "CONTAINS_ANY": TokenType.CONTAINS_ANY,
    "CONTAINS_ALL": TokenType.CONTAINS_ALL,
    "COUNT": TokenType.COUNT,
    "SUM": TokenType.SUM,
    "AVG": TokenType.AVG,
    "MAX": TokenType.MAX,
    "MIN": TokenType.MIN,
    "COLLECT": TokenType.COLLECT,
    "LENGTH": TokenType.LENGTH,
    "NODES": TokenType.NODES,
    "TRUE": TokenType.BOOLEAN,
    "FALSE": TokenType.BOOLEAN,
    "NULL": TokenType.NULL,
}


class Lexer:
    """Lexical analyzer for VQL 2.0."""

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: list[Token] = []

    def current_char(self) -> str | None:
        """Get current character or None if at end."""
        if self.pos >= len(self.text):
            return None
        return self.text[self.pos]

    def peek(self, offset: int = 1) -> str | None:
        """Peek ahead at character."""
        pos = self.pos + offset
        if pos >= len(self.text):
            return None
        return self.text[pos]

    def advance(self) -> str | None:
        """Move to next character."""
        char = self.current_char()
        if char is not None:
            self.pos += 1
            if char == "\n":
                self.line += 1
                self.column = 1
            else:
                self.column += 1
        return char

    def skip_whitespace(self) -> None:
        """Skip whitespace but track newlines."""
        while self.current_char() is not None and self.current_char() in " \t\r\n":
            self.advance()

    def skip_comment(self) -> None:
        """Skip single-line comment (-- ...) or block comment (/* ... */)."""
        if self.current_char() == "-" and self.peek() == "-":
            # Line comment
            while self.current_char() is not None and self.current_char() != "\n":
                self.advance()
        elif self.current_char() == "/" and self.peek() == "*":
            # Block comment
            self.advance()  # /
            self.advance()  # *
            while self.current_char() is not None:
                if self.current_char() == "*" and self.peek() == "/":
                    self.advance()  # *
                    self.advance()  # /
                    break
                self.advance()

    def read_string(self) -> str:
        """Read string literal."""
        quote = self.current_char()
        start_line = self.line
        start_column = self.column
        self.advance()  # Opening quote

        value = ""
        while self.current_char() is not None and self.current_char() != quote:
            if self.current_char() == "\\":
                self.advance()
                escaped = self.current_char()
                if escaped == "n":
                    value += "\n"
                elif escaped == "t":
                    value += "\t"
                elif escaped == "\\":
                    value += "\\"
                elif escaped == quote:
                    value += quote
                else:
                    value += escaped or ""
                self.advance()
            else:
                value += self.current_char() or ""
                self.advance()

        if self.current_char() != quote:
            raise LexerError(
                f"Unterminated string literal",
                start_line,
                start_column,
                hint=f"Add closing {quote}",
            )

        self.advance()  # Closing quote
        return value

    def read_number(self) -> Token:
        """Read numeric literal."""
        start_line = self.line
        start_column = self.column
        num_str = ""

        while self.current_char() is not None and (self.current_char().isdigit() or self.current_char() == "."):
            num_str += self.current_char()
            self.advance()

        # Check for scientific notation
        if self.current_char() in ("e", "E"):
            num_str += self.current_char()
            self.advance()
            if self.current_char() in ("+", "-"):
                num_str += self.current_char()
                self.advance()
            while self.current_char() is not None and self.current_char().isdigit():
                num_str += self.current_char()
                self.advance()

        if "." in num_str or "e" in num_str or "E" in num_str:
            return Token(TokenType.FLOAT, float(num_str), start_line, start_column, num_str)
        else:
            return Token(TokenType.INTEGER, int(num_str), start_line, start_column, num_str)

    def read_identifier(self) -> Token:
        """Read identifier or keyword."""
        start_line = self.line
        start_column = self.column
        ident = ""

        while self.current_char() is not None and (
            self.current_char().isalnum() or self.current_char() in "_-"
        ):
            ident += self.current_char()
            self.advance()

        # Check if it's a keyword
        upper_ident = ident.upper()
        if upper_ident in KEYWORDS:
            token_type = KEYWORDS[upper_ident]
            if token_type == TokenType.BOOLEAN:
                value = upper_ident == "TRUE"
            else:
                value = ident
            return Token(token_type, value, start_line, start_column, ident)

        return Token(TokenType.IDENTIFIER, ident, start_line, start_column, ident)

    def tokenize(self) -> list[Token]:
        """Tokenize the input text."""
        self.tokens = []

        while self.current_char() is not None:
            # Skip whitespace and comments
            if self.current_char() in " \t\r\n":
                self.skip_whitespace()
                continue

            if self.current_char() == "-" and self.peek() == "-":
                self.skip_comment()
                continue

            if self.current_char() == "/" and self.peek() == "*":
                self.skip_comment()
                continue

            line = self.line
            column = self.column
            char = self.current_char()

            # String literals
            if char in ("'", '"'):
                value = self.read_string()
                self.tokens.append(Token(TokenType.STRING, value, line, column, f"{char}{value}{char}"))
                continue

            # Numbers
            if char.isdigit():
                self.tokens.append(self.read_number())
                continue

            # Identifiers and keywords
            if char.isalpha() or char == "_":
                self.tokens.append(self.read_identifier())
                continue

            # Two-character operators
            if char == "-" and self.peek() == ">":
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.ARROW_RIGHT, "->", line, column, "->"))
                continue

            if char == "<" and self.peek() == "-":
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.ARROW_LEFT, "<-", line, column, "<-"))
                continue

            if char == "!" and self.peek() == "=":
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.NEQ, "!=", line, column, "!="))
                continue

            if char == ">" and self.peek() == "=":
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.GTE, ">=", line, column, ">="))
                continue

            if char == "<" and self.peek() == "=":
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.LTE, "<=", line, column, "<="))
                continue

            if char == "." and self.peek() == ".":
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.DOTDOT, "..", line, column, ".."))
                continue

            # Single-character tokens
            single_char_tokens = {
                "(": TokenType.LPAREN,
                ")": TokenType.RPAREN,
                "[": TokenType.LBRACKET,
                "]": TokenType.RBRACKET,
                "{": TokenType.LBRACE,
                "}": TokenType.RBRACE,
                ",": TokenType.COMMA,
                ".": TokenType.DOT,
                ":": TokenType.COLON,
                ";": TokenType.SEMICOLON,
                "-": TokenType.DASH,
                "*": TokenType.STAR,
                "+": TokenType.PLUS,
                "/": TokenType.SLASH,
                "%": TokenType.PERCENT,
                "=": TokenType.EQ,
                ">": TokenType.GT,
                "<": TokenType.LT,
            }

            if char in single_char_tokens:
                token_type = single_char_tokens[char]
                self.advance()
                self.tokens.append(Token(token_type, char, line, column, char))
                continue

            # Unknown character
            raise LexerError(
                f"Unexpected character: {char!r}",
                line,
                column,
                hint="Remove or escape this character",
            )

        # Add EOF token
        self.tokens.append(Token(TokenType.EOF, None, self.line, self.column, ""))
        return self.tokens
