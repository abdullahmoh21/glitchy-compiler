import unittest
from Compiler.utils import *
from Compiler.Analyzer import *

class TestAnalyzer(unittest.TestCase):
    def setUp(self):
        error.clear_errors()

    # TODO: add string concatenation tests about 5
    def test_duplicate_variable(self):
        ast = Program([
            VariableDeclaration('x', Integer(5)),
            VariableDeclaration('x', Integer(10), line=2),  # Duplicate variable declaration
        ])
        analyzer = SemanticAnalyzer(ast)
        symbol_table = analyzer.analyze()
        self.assertTrue(error.has_error_occurred())
        self.assertTrue(any("ReferenceError: The name 'x' on line 2 is already defined." in e for e in error.get_errors()))

    def test_invalid_comparison(self):
        ast = Program([
            VariableDeclaration('a', String("hello")),
            VariableDeclaration('b', Integer(2), line=2),
            FunctionCall('print',[Argument(Comparison(VariableReference('a', 3), '<', VariableReference('b', 3), line=3))], line=3),
        ])
        analyzer = SemanticAnalyzer(ast)
        symbol_table = analyzer.analyze()
        self.assertTrue(error.has_error_occurred())
        self.assertTrue(any("Type mismatch in comparison" in e for e in error.get_errors()))

    def test_logical_operation(self):
        ast = Program([
            VariableDeclaration('a', Boolean('true')),    # set a = true
            VariableDeclaration('b', Boolean('false')),   # set b = false
            FunctionCall('print',[Argument(LogicalOp(VariableReference('a'), '&&', VariableReference('b')))]),    # print(a && b)
        ])
        analyzer = SemanticAnalyzer(ast)
        _, symbol_table = analyzer.analyze()
        self.assertFalse(error.has_error_occurred())
        self.assertIsNotNone(symbol_table)
        self.assertIsNotNone(symbol_table.isDeclared('a'))
        self.assertIsNotNone(symbol_table.isDeclared('b'))
        self.assertEqual(symbol_table.getType('a'), 'boolean')
        self.assertEqual(symbol_table.getType('b'), 'boolean')

    def test_invalid_logical_operation(self):
        ast = Program([
            VariableDeclaration('a', Integer(1),line=1),
            VariableDeclaration('b', Boolean('false'),line=2),
            FunctionCall('print',[Argument(LogicalOp(VariableReference('a',line=3), '&&', VariableReference('b',line=3),line=3))],line=3),
        ])
        analyzer = SemanticAnalyzer(ast)
        symbol_table = analyzer.analyze()
        self.assertTrue(error.has_error_occurred())
        self.assertTrue(any("TypeError: Invalid expression on line 3. Please ensure correct types are being compared: 'a' '&&' 'b'" in e for e in error.get_errors()))

    def test_variable_incorrect_type(self):
        ast = Program([
            VariableDeclaration('x', Double(3.5),annotation="integer")
        ])
        analyzer = SemanticAnalyzer(ast)
        analyzer.analyze()
        self.assertTrue(error.has_error_occurred())
        self.assertTrue(any("TypeError: Variable 'x' expects type 'integer' but got expression: '3.5' of type 'double'" in e for e in error.get_errors()))

    def test_undefined_variable_usage(self):
        ast = Program([
            VariableUpdated('y', Integer(1))
        ])
        analyzer = SemanticAnalyzer(ast)
        analyzer.analyze()
        self.assertTrue(error.has_error_occurred())
        self.assertTrue(any("ReferenceError: Variable 'y' does not exist in this scope" in e for e in error.get_errors()))

    def test_variable_redefinition(self):
        ast = Program([
            VariableDeclaration('z', Integer(10),line=1),
            VariableDeclaration('z', Double(10.5),line=1)
        ])
        analyzer = SemanticAnalyzer(ast)
        analyzer.analyze()
        self.assertTrue(error.has_error_occurred())
        self.assertTrue(any("ReferenceError: The name 'z' on line 1 is already defined." in e for e in error.get_errors()))

    def test_variable_shadowing(self):
        ast = Program([
            VariableDeclaration('a', Integer(5)),
            FunctionDeclaration('testScope', 'void', [], Block([
                VariableDeclaration('a', Double(5.0))
            ]))
        ])
        analyzer = SemanticAnalyzer(ast)
        analyzer.analyze()
        self.assertFalse(error.has_error_occurred())

    def test_invalid_function_call(self):
        ast = Program([
            FunctionCall('foo', [],line=1),
            FunctionDeclaration('foo', 'void', [], Block([]),line=2)
        ])
        analyzer = SemanticAnalyzer(ast)
        analyzer.analyze()
        self.assertTrue(error.has_error_occurred())
        self.assertTrue(any("ReferenceError: Incorrect Function Call on line 1. A function with name 'foo' does not exist." in e for e in error.get_errors()))

    def test_function_return(self):
        ast = Program([
            FunctionDeclaration('add', 'integer', [Parameter('x', 'integer'), Parameter('y', 'integer')], Block([
                VariableDeclaration('sum', BinaryOp(VariableReference('x'), '+', VariableReference('y')))
            ]), line=1)
        ])
        analyzer = SemanticAnalyzer(ast)
        analyzer.analyze()
        self.assertTrue(error.has_error_occurred())
        self.assertTrue(any("ReturnError: Not all branches in the function 'add' return correctly" in e for e in error.get_errors()))

    def test_function_return_1(self):
        ast = Program([
            FunctionDeclaration('testFunc', 'integer', [], Block([
                If(
                    Comparison(Integer(1), '<', Integer(2)),  # Condition always true
                    Block([Return(Integer(1))]),  # This branch returns
                    Block([  # The else branch does not return
                        FunctionCall('print', [Argument(String("No return here"))], line=3)
                    ])
                )
            ]), line=2),
            FunctionCall('testFunc', [], line=5)
        ])
        analyzer = SemanticAnalyzer(ast)
        analyzer.analyze()
        self.assertTrue(error.has_error_occurred())
        self.assertTrue(any("Not all branches in the function 'testFunc' return correctly" in e for e in error.get_errors()))

    def test_function_return_2(self):
        ast = Program([
            FunctionDeclaration('checkValue', 'integer', [], Block([
                VariableDeclaration('x', Integer(10), line=2),
                If(
                    Comparison(VariableReference('x'), '==', Integer(10)),
                    Block([Return(Integer(10))]),  # Return in if branch
                    [  # Elif with no return
                        If(
                            Comparison(VariableReference('x'), '==', Integer(5)),
                            Return(Integer(5)),  # Return in elif branch
                            # No else block or return
                        )
                    ]
                )
            ]), line=1),
            FunctionCall('checkValue', [], line=4)
        ])
        analyzer = SemanticAnalyzer(ast)
        analyzer.analyze()
        self.assertTrue(error.has_error_occurred())
        self.assertTrue(any("Not all branches in the function 'checkValue' return correctly" in e for e in error.get_errors()))

    def test_function_return_3(self):
        ast = Program([
            FunctionDeclaration('loopFunc', 'integer', [], Block([
                While(
                    Comparison(Integer(15), '<', Integer(10)),
                    Block([
                        If(
                            Comparison(Integer(10), '==', Integer(5)),
                            Return(Integer(5)),  # Return when i is 5
                            # No else block or return
                        )
                    ])
                )
            ]), line=1),
            FunctionCall('loopFunc', [], line=5)
        ])
        analyzer = SemanticAnalyzer(ast)
        analyzer.analyze()
        self.assertTrue(error.has_error_occurred())
        self.assertTrue(any("Not all branches in the function 'loopFunc' return correctly" in e for e in error.get_errors()))

    def test_function_return_4(self):
        ast = Program([
            FunctionDeclaration('exampleFunc', 'integer', [], Block([
                If(
                    Comparison(Integer(10), '>', Integer(0)),
                    Block([Return(Integer(1))]),
                    elseBlock=Block([Return(Integer(2))])  # Return in else block
                )
            ]), line=1),
            FunctionCall('exampleFunc', [], line=4)
        ])
        analyzer = SemanticAnalyzer(ast)
        analyzer.analyze()
        self.assertFalse(error.has_error_occurred())  # Should pass, since all paths return

    def test_function_return_5(self):
        ast = Program([
            FunctionDeclaration('multiCheck', 'integer', [], Block([
                If(
                    Comparison(Integer(10), '==', Integer(0)),
                    Block([Return(Integer(0))]),  # Return in if branch
                    If(
                        Comparison(Integer(10), '==', Integer(1)),
                        Block([Return(Integer(1))]),  # Return in nested if branch
                        # No else block or return
                    )
                )
            ]), line=1),
            FunctionCall('multiCheck', [],line=4)
        ])
        analyzer = SemanticAnalyzer(ast)
        analyzer.analyze()
        self.assertTrue(error.has_error_occurred())
        self.assertTrue(any("Not all branches in the function 'multiCheck' return correctly" in e for e in error.get_errors()))
    
    def test_function_return_6(self):
        ast = Program([
            FunctionDeclaration('square', 'integer', [], Block([
                Return(String("text"),line=2)
            ]),line=1)
        ])
        analyzer = SemanticAnalyzer(ast)
        analyzer.analyze()
        self.assertTrue(error.has_error_occurred())
        self.assertTrue(any("TypeError: Return Type error on line 2. Expected return of type 'integer' for function 'square' got: 'string' instead." in e for e in error.get_errors()))

    def test_string_cat_1(self):
        pass
    
    def test_string_cat_2(self):
        pass
    
    def test_string_cat_3(self):
        pass
    
    def test_string_cat_4(self):
        pass
    
    def test_string_cat_5(self):
        pass
    
    def test_invalid_argument_type(self):
        ast = Program([
            FunctionDeclaration('testFunc', 'void', [Parameter('x', 'integer')], Block([
                FunctionCall('print',[Argument(VariableReference('x'))])
            ])),
            FunctionCall('testFunc', [String("string")],line=3)
        ])
        analyzer = SemanticAnalyzer(ast)
        analyzer.analyze()
        self.assertTrue(error.has_error_occurred())
        self.assertTrue(any("TypeError: Incorrect Function Call on line 3. Expected type 'integer' for parameter 'x' got type 'string'" in e for e in error.get_errors()))

    def test_missing_argument(self):
        ast = Program([
            FunctionDeclaration('testFunc', 'void', [Parameter('x', 'integer')], Block([
                FunctionCall('print',[Argument(VariableReference('x'))], line=1),
            ]),line=1),
            FunctionCall('testFunc', [], line=3)
        ])
        analyzer = SemanticAnalyzer(ast)
        analyzer.analyze()
        self.assertTrue(error.has_error_occurred())
        self.assertTrue(any("ArgumentError on line 3: Function 'testFunc' expects 1 arguments but received 0 arguments" in e for e in error.get_errors()))

    def test_correct_recursion(self):
        ast = Program([
            FunctionDeclaration('factorial', 'integer', [Parameter('n', 'integer')], Block([
                If(
                    Comparison(Integer(10), '<=', Integer(1)),
                    Block([Return(Integer(1))]),
                    elseBlock=Block([
                        Return(BinaryOp(Integer(10), '*', FunctionCall('factorial', [BinaryOp(Integer(10), '-', Integer(1))])))
                    ])
                )
            ])),
            FunctionCall('factorial', [Argument(Integer(5))])
        ])
        analyzer = SemanticAnalyzer(ast)
        analyzer.analyze()
        self.assertFalse(error.has_error_occurred())

    def test_invalid_recursion_call(self):
        ast = Program([
            FunctionDeclaration('factorial', 'int', [Parameter('n', 'int')], Block([
                Return(FunctionCall('factorial', []))
            ])),
            FunctionCall('factorial', [Argument(Integer(5))], None)
        ])
        analyzer = SemanticAnalyzer(ast)
        analyzer.analyze()
        self.assertTrue(error.has_error_occurred())
        self.assertTrue(any("ArgumentError: Function 'factorial' expects 1 arguments but received 0 arguments" in e for e in error.get_errors()))

if __name__ == '__main__':
    unittest.main()