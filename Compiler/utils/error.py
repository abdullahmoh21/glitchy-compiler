from .ast import *
"""
This module defines all the exceptions that can be raised by the compiler. As well as methods to report or throw these errors 
"""

error_occurred = False
error_messages = []
red = "\033[31m"
reset = "\033[0m"

def throw(exception, exit=True, line=None):
    """
    Raises an exception and handles it by printing only the error message without a stack trace.
    This hides python from the user. We can also raise an Exit exception that exits compilation, from wherever we are in the compilation process
    
    Args:
        exception (Error): The exception instance to raise and handle.
    """
    global error_occurred, error_messages
    error_occurred = True
    try:
        raise exception
    except Error as e:
        _ = f" on line {line}" if line is not None else ""
        ty = f"{type(e).__name__}{_}:"
        msg = str(e).split(":", 1)[-1].strip()
        
        error_messages.append(f"{ty} {msg}")
        print(f"{red}{ty}{reset} {msg}")
        
        if exit:
            raise ExitSignal()

def report(message, type_="Complier",error=True, line=None):
    """
    Prints an error message to standard output without exiting the program. 
    Marks that code is erroneous so that further execution can be stopped.

    Args:
        message (str): The error message to report.
        type_ (str): The type of error (e.g., Syntax, Lexer, etc.).
        error(bool, optional): wether to mark global error flag. 
        line (int, optional): The line number where the error occurred.
    """
    global error_occurred, error_messages
    if error:   # warnings are not errors
        error_occurred = True
    heading = f"{red}{type_}" if type_ == "Warning" else f"{red}{type_} Error"
    if line is not None:
        error_message = f"{heading} at line {line}: {reset}{message}"
    else:
        error_message = f"{heading}: {reset}{message}"
    
    error_messages.append(error_message)
    print(error_message)

def has_error_occurred():
    global error_occurred
    return error_occurred

def get_errors():
    global error_messages
    return error_messages

def clear_errors(): 
    """
    Clears the error flag and the list of error messages.
    """
    global error_occurred, error_messages
    error_messages = []  # Reset the list of error messages
    error_occurred = False  # Reset the error flag

class Error(Exception):
    """Base class for all compiler-related errors."""
    def __init__(self, message):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"{self.message}"

class SyntaxError(Error):
    """Exception raised for syntax errors."""
    def __init__(self, message, line):
        super().__init__(message)
        self.line = line

    def __str__(self):
        return f"SyntaxError: {self.message} at line {self.line}"

class SemanticError(Error):
    """Exception raised for semantic errors."""
    def __init__(self, message):
        super().__init__(message)

    def __str__(self):
        return f"{self.message}"

class ParsingError(Error):
    """Exception raised for parsing errors."""
    def __init__(self, message):
        super().__init__(message)

    def __str__(self):
        return f"{self.message}"

class ExitSignal(Error):
    """Exception raised to exit a compilation stage"""
    def __init__(self):
        super().__init__(None)
        
    def __str__(self):
        return "Exit Exception"

class TypeError(Error):
    """Exception raised for type mismatches or illegal operations."""
    def __init__(self, message):
        super().__init__(message)

    def __str__(self):
        return f"TypeError: {self.message}"

class ReturnError(Error):
    """Exception raised for Return errors."""
    def __init__(self, message):
        super().__init__(message)

    def __str__(self):
        return f"ReturnError: {self.message}"

class ArgumentError(Error):
    """Exception raised for function and method arguments"""
    def __init__(self, message):
        super().__init__(message)

    def __str__(self):
        return f"ArgumentError: {self.message}"

class ReferenceError(Error):
    """Exception raised for incorrect references"""
    def __init__(self, message):
        super().__init__(message)

    def __str__(self):
        return f"ReferenceError: {self.message}"

class CompilationError(Error):
    """Exception raised for all generator errors"""
    def __init__(self, message):
        super().__init__(message)

    def __str__(self):
        return f"CompilationError: {self.message}"

class GlitchError(Error):
    """Exception raised for all errors in our glitch game"""
    def __init__(self, message):
        super().__init__(message)

    def __str__(self):
        return f"GlitchError: {self.message}"
