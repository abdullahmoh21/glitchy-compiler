"""
Stores all builtin function data
Even though this is overkill for three functions but adding more in future will be easier
"""
from .ast import *

class BuiltInFunctions:
    BUILTINS = {
        'typeof': {
            'name': 'typeof',
            'parameters': [Parameter('', 'any')],
            'arity': 1,
            'return_type': 'string'
        },
        'print': {
            'name': 'print',
            'parameters': [Parameter('', 'any')],
            'arity': 1,
            'return_type': 'void'
        },
        'input': {
            'name': 'input',
            'parameters': [],
            'arity': 0,
            'return_type': 'string'
        },
        'glitch': {
            'name': 'glitch',
            'parameters': [],
            'arity': 0,
            'return_type': 'void'
        }
    }

    @classmethod
    def getAll(cls):
        return list(cls.BUILTINS.values())