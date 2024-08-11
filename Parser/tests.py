import unittest
import sys
import os
from Lexer import *
from Parser import *
from Ast import *
from Error import report


#  All my parser tests are in this class. to run all tests: python3 -m unittest parsing.tests
class TestParser(unittest.TestCase):

    def test_simple_set_and_print(self):
        source_code = '''
        set x = 42
        print("Hello, world")
        '''
        expected_ast = Program([
            VariableDeclaration("x", Integer(42), 2),
            Print(String("Hello, world"), 3)
        ], 1)
        self.run_test(source_code, expected_ast)

    def test_if_statement(self):
        source_code = '''   
        set x = 10
        if (x == 10) {
            print("x is ten")
        }
        '''
        expected_ast = Program([
            VariableDeclaration("x", Integer(10), 2),
            If(
                Comparison(VariableReference("x", 3), "==", Integer(10, 3), 3),
                Block([
                    Print(String("x is ten"), 4)
                ]),
                3
            )
        ], 1)
        self.run_test(source_code, expected_ast)

    def test_elseif_statement(self):
        source_code = '''
        set x = 5
        if (x > 10) {
            print("x is greater than ten")
        } elif (x < 10) {
            print("x is less than ten")
        } else {
            print("x is ten")
        }
        '''
        expected_ast = Program([
            VariableDeclaration("x", Integer(5), 2),
            If(
                Comparison(VariableReference("x", 3), ">", Integer(10, 3), 3),
                Block([
                    Print(String("x is greater than ten"), 4)
                ]),
                elifNodes=[
                    (
                        Comparison(VariableReference("x", 5), "<", Integer(10, 5), 5),
                        Block([
                            Print(String("x is less than ten"), 6)
                        ])
                    )
                ],
                elseBlock=Block([
                    Print(String("x is ten"), 8)
                ]),
                line=3
            )
        ], 1)

        
        self.run_test(source_code, expected_ast)

    def test_nested_if_statement(self):
        source_code = '''
        set x = 10
        if (x > 1) {
            if (x > 5) {
                if (x == 10) {
                    print("x is ten")
                }
            }
        }
        '''
        expected_ast = Program([
            VariableDeclaration("x", Integer(10), 2),
            If(
                Comparison(VariableReference("x", 3), ">", Integer(1, 3), 3),
                Block([
                    If(
                        Comparison(VariableReference("x", 4), ">", Integer(5, 4), 4),
                        Block([
                            If(
                                Comparison(VariableReference("x", 5), "==", Integer(10, 5), 5),
                                Block([
                                    Print(String("x is ten"), 6)
                                ]),
                                5
                            )
                        ]),
                        4
                    )
                ]),
                3
            )
        ], 1)
        self.run_test(source_code, expected_ast)

    def test_while_loop(self):
        source_code = '''
        set x = 0
        while (x < 10) {
            x = x + 1
        }
        '''
        expected_ast = Program([
            VariableDeclaration("x", Integer(0), 2),
            While(
                Comparison(VariableReference("x", Integer(3)), "<", Integer(10, 3), 3),
                Block([
                    VariableUpdated("x", BinaryOp(
                        VariableReference("x", 4), "+", Integer(1, 4), 4
                    ), 4)
                ]),
                3
            )
        ], 1)
        self.run_test(source_code, expected_ast)

    def test_input_statement(self):
        source_code = '''
        input foo
        print(foo)
        '''
        expected_ast = Program([
            Input(VariableReference("foo", 2), 2),
            Print(VariableReference("foo", 3), 3)
        ], 1)
        self.run_test(source_code, expected_ast)

    def test_complex_expression(self):
        source_code = '''
        set result = (a + b) * (c - d) / e
        '''
        expected_ast = Program([
            VariableDeclaration("result", 
                BinaryOp(
                    BinaryOp(
                        BinaryOp(
                            VariableReference("a", 2), "+", VariableReference("b", 2), 2
                        ),
                        "*",
                        BinaryOp(
                            VariableReference("c", 2), "-", VariableReference("d", 2), 2
                        ),
                        2
                    ),
                    "/",
                    VariableReference("e", 2), 2
                ), 2
            )
        ], 1)
        self.run_test(source_code, expected_ast)
    
    def test_complex_expression_1(self):
        source_code = '''
        set result = x + y > z && w == 1
        '''
        
        expected_ast = Program([
            VariableDeclaration(
                "result",
                LogicalOp(
                    Comparison(
                        BinaryOp(
                            VariableReference("x", 2),
                            "+",
                            VariableReference("y", 2),
                            2
                        ),
                        ">",
                        VariableReference("z", 2),
                        2
                    ),
                    "&&",
                    Comparison(
                        VariableReference("w", 2),
                        "==",
                        Integer(1, 2),
                        2
                    ),
                    2
                ), 2
            )
        ], 1)

        self.run_test(source_code, expected_ast)

    def test_nested_logical_and_comparison(self):
        source_code = '''
        set result = (x + y > z && w == 1) || (a * b < c - d)
        '''
        
        expected_ast = Program([
            VariableDeclaration(
                "result",
                LogicalOp(
                    LogicalOp(
                        Comparison(
                            BinaryOp(
                                VariableReference("x", 2),
                                "+",
                                VariableReference("y", 2),
                                2
                            ),
                            ">",
                            VariableReference("z", 2),
                            2
                        ),
                        "&&",
                        Comparison(
                            VariableReference("w", 2),
                            "==",
                            Integer(1, 2),
                            2
                        ),
                        2
                    ),
                    "||",
                    Comparison(
                        BinaryOp(
                            VariableReference("a", 2),
                            "*",
                            VariableReference("b", 2),
                            2
                        ),
                        "<",
                        BinaryOp(
                            VariableReference("c", 2),
                            "-",
                            VariableReference("d", 2),
                            2
                        ),
                        2
                    ),
                    2
                ), 2
            )
        ], 1)

        self.run_test(source_code, expected_ast)

    def test_mixed_arithmetic_comparison_logical(self):
        source_code = '''
        set result = ((x + y * z) > (w - 1) && (a / b) <= (c + d)) || e != f
        '''
        
        expected_ast = Program([
            VariableDeclaration(
                "result",
                LogicalOp(
                    LogicalOp(
                        Comparison(
                            BinaryOp(
                                VariableReference("x", 2),
                                "+",
                                BinaryOp(
                                    VariableReference("y", 2),
                                    "*",
                                    VariableReference("z", 2),
                                    2
                                ),
                                2
                            ),
                            ">",
                            BinaryOp(
                                VariableReference("w", 2),
                                "-",
                                Integer(1, 2),
                                2
                            ),
                            2
                        ),
                        "&&",
                        Comparison(
                            BinaryOp(
                                VariableReference("a", 2),
                                "/",
                                VariableReference("b", 2),
                                2
                            ),
                            "<=",
                            BinaryOp(
                                VariableReference("c", 2),
                                "+",
                                VariableReference("d", 2),
                                2
                            ),
                            2
                        ),
                        2
                    ),
                    "||",
                    Comparison(
                        VariableReference("e", 2),
                        "!=",
                        VariableReference("f", 2),
                        2
                    ),
                    2
                ), 2
            )
        ], 1)

        self.run_test(source_code, expected_ast)

    def test_deeply_nested_parentheses(self):
        source_code = '''
        set result = ((((x + 1) * (y - 2)) / 3) == z) && !(a || b)
        '''
        
        expected_ast = Program([
            VariableDeclaration(
                name='result',
                expression=LogicalOp(
                    operator='&&',
                    left=Comparison(
                        operator='==',
                        left=BinaryOp(
                            operator='/',
                            left=BinaryOp(
                                operator='*',
                                left=BinaryOp(
                                    operator='+',
                                    left=VariableReference(name='x',line=1),
                                    right=Integer(value=1),
                                    line=1  
                                ),
                                right=BinaryOp(
                                    operator='-',
                                    left=VariableReference(name='y',line=1),
                                    right=Integer(value=2),
                                    line=1  
                                ),
                                line=1  
                            ),
                            right=Integer(value=3),
                            line=1  
                        ),
                        right=VariableReference(name='z',line=1),
                        line=1  
                    ),
                    right=UnaryOp(
                        operator='!',
                        left=LogicalOp(
                            operator='||',
                            left=VariableReference(name='a',line=1),
                            right=VariableReference(name='b',line=1),
                            line=1  
                        ),
                        line=1  
                    ),
                    line=1  
                ),
                line=1  
            )
        ])  
        self.run_test(source_code, expected_ast)
        
    def test_multiple_levels_of_operations(self):
        source_code = '''
        set result = ((x + y) * (z - w)) / ((a + b) * (c - d)) + e
        '''
        
        expected_ast = Program([
            VariableDeclaration(
                'result',
                expression=BinaryOp(
                    operator='+',
                    left=BinaryOp(
                        operator='/',
                        left=BinaryOp(
                            operator='*',
                            left=BinaryOp(
                                operator='+',
                                left=VariableReference(name='x',line =1),
                                right=VariableReference(name='y',line =1),
                                line=1
                            ),
                            right=BinaryOp(
                                operator='-',
                                left=VariableReference(name='z',line =1),
                                right=VariableReference(name='w',line =1),
                                line=1
                            ),
                            line=1
                        ),
                        right=BinaryOp(
                            operator='*',
                            left=BinaryOp(
                                operator='+',
                                left=VariableReference(name='a',line =1),
                                right=VariableReference(name='b',line =1),
                                line=1
                            ),
                            right=BinaryOp(
                                operator='-',
                                left=VariableReference(name='c',line =1),
                                right=VariableReference(name='d',line =1),
                                line=1
                            ),
                            line=1
                        ),
                        line=1
                    ),
                    right=VariableReference(name='e',line =1),
                    line=1
                ),
                line=1
            )
        ])

        
        self.run_test(source_code, expected_ast)

    def test_expression_with_unary_operators(self):
        source_code = '''
        set result = -x + y * -z
        '''
        
        expected_ast = Program([
            VariableDeclaration(
                "result",
                BinaryOp(
                    UnaryOp(
                        "-",
                        VariableReference("x", 2),
                        2
                    ),
                    "+",
                    BinaryOp(
                        VariableReference("y", 2),
                        "*",
                        UnaryOp(
                            "-",
                            VariableReference("z", 2),
                            2
                        ),
                        2
                    ),
                    2
                ), 2
            )
        ], 1)

        self.run_test(source_code, expected_ast)

    def test_nested_blocks(self):
        source_code = '''
        set x = 1
        if (x == 1) {
            set y = 2
            if (y == 2) {
                print("y is two")
            }
        }
        '''
        expected_ast = Program([
            VariableDeclaration("x", Integer(1), 2),
            If(
                Comparison(VariableReference("x", 3), "==", Integer(1, 3), 3),
                Block([
                    VariableDeclaration("y", Integer(2), 4),
                    If(
                        Comparison(VariableReference("y", 5), "==", Integer(2, 5), 5),
                        Block([
                            Print(String("y is two"), 6)
                        ]),
                        5
                    )
                ]),
                3
            )
        ], 1)
        self.run_test(source_code, expected_ast)

    def test_expression_with_parentheses(self):
        source_code = '''
        set result = (a + (b * c) - d) / e
        '''
        expected_ast = Program([
            VariableDeclaration("result", 
                BinaryOp(
                    BinaryOp(
                        BinaryOp(
                            VariableReference("a", 2),
                            "+",
                            BinaryOp(
                                VariableReference("b", 2), "*", VariableReference("c", 2), 2
                            ),
                            2
                        ),
                        "-",
                        VariableReference("d", 2),
                        2
                    ),
                    "/",
                    VariableReference("e", 2),
                    2
                ), 2
            )
        ], 1)
        self.run_test(source_code, expected_ast)

    def test_empty_block(self):
        source_code = '''
        set x = 10
        if (x > 5) {
        }
        '''
        expected_ast = Program([
            VariableDeclaration("x", Integer(10), 2),
            If(
                Comparison(VariableReference("x", 3), ">", Integer(5, 3), 3),
                Block([]),
                3
            )
        ], 1)
        self.run_test(source_code, expected_ast)

    def test_for_loop_with_complex_update(self):
        source_code = '''
        for (i = 0; i < 10; i = i + 2) {
            print("Looping")
        }
        '''
        expected_ast = Program([
            Block([
                VariableDeclaration("i", Integer(0), 2),  # Initialization
                While(
                    Comparison(VariableReference("i", 2), "<", Integer(10, 2), 2),  # Condition
                    Block([
                        Print(String("Looping"), 3),
                        VariableUpdated("i",BinaryOp(VariableReference("i", 3), "+", Integer(2, 3), 3), 3)  # Increment
                    ]),
                    2
                )
            ])
        ], 1)
        self.run_test(source_code, expected_ast)

    def test_for_loop(self):
        source_code = '''
        for (i = 0; i < 10; i++) {
            print("Looping")
        }
        '''
        expected_ast = Program([
            Block([
                VariableDeclaration("i", Integer(0), 2),  # Initialization
                While(
                    Comparison(VariableReference("i", 2), "<", Integer(10, 2), 2),  # Condition
                    Block([
                        Print(String("Looping"), 3),
                        VariableUpdated("i", BinaryOp(VariableReference("i", 3), "+", Integer(1, 3), 3), 3)  # Increment
                    ]),
                    2
                )
            ])
        ], 1)
        self.run_test(source_code, expected_ast)
        
    def run_test(self, source_code, expected_ast):
        lexer = Lexer(source_code)
        parser = Parser(lexer)
        generated_ast = parser.parse()
        
        if generated_ast is not None:
            print("\nGenerated AST:")
            generated_ast.print_content()
        
        print("\nExpected AST:")
        expected_ast.print_content()
        print("\n")
        
        if not TestParser.compare_ast(generated_ast, expected_ast):
            self.fail("\n[ERROR] Generated AST does not match expected AST\n")
    
    @staticmethod
    def compare_ast(generated, expected, path=""):
        if type(generated) != type(expected):
            print(f"Type mismatch at {path}: {type(generated).__name__} != {type(expected).__name__}")
            return False

        if isinstance(generated, Program):
            if len(generated.statements) != len(expected.statements):
                print(f"Integer of statements mismatch at {path}: {len(generated.statements)} != {len(expected.statements)}")
                return False
            for i, (stmt1, stmt2) in enumerate(zip(generated.statements, expected.statements)):
                if not TestParser.compare_ast(stmt1, stmt2, path + f".statements[{i}]"):
                    return False

        elif isinstance(generated, VariableDeclaration):
            if generated.name != expected.name:
                print(f"VariableDeclaration name mismatch at {path}: {generated.name} != {expected.name}")
                return False
            if not TestParser.compare_ast(generated.value, expected.value, path + ".value"):
                print(f"VariableDeclaration's value mismatch at {path}: {generated.value} != {expected.value}")
                return False

        elif isinstance(generated, VariableUpdated):
            if generated.name != expected.name:
                print(f"VariableUpdated name mismatch at {path}: {generated.name} != {expected.name}")
                return False
            if not TestParser.compare_ast(generated.value, expected.value, path + ".value"):
                print(f"VariableUpdated's value mismatch at {path}: {generated.value} != {expected.value}")
                return False

        elif isinstance(generated, VariableReference):
            if generated.name != expected.name:
                print(f"VariableReference name mismatch at {path}: {generated.name} != {expected.name}")
                return False

        elif isinstance(generated, Print):
            if not TestParser.compare_ast(generated.expression, expected.expression, path + ".expression"):
                return False

        elif isinstance(generated, If):
            if not TestParser.compare_ast(generated.comparison, expected.comparison, path + ".comparison"):
                return False
            if len(generated.block.statements) != len(expected.block.statements):
                print(f"If statement block number of statements mismatch at {path}: {len(generated.block.statements)} != {len(expected.block.statements)}")
                return False
            for i, (stmt1, stmt2) in enumerate(zip(generated.block.statements, expected.block.statements)):
                if not TestParser.compare_ast(stmt1, stmt2, path + f".block.statements[{i}]"):
                    return False
                
        elif isinstance(generated, While):
            print(f"Generated While block statements count: {len(generated.block.statements)} at {path}")
            print(f"Expected While block statements count: {len(expected.block.statements)} at {path}")
            if not TestParser.compare_ast(generated.comparison, expected.comparison, path + ".comparison"):
                return False
            if len(generated.block.statements) != len(expected.block.statements):
                print(f"While statement block number of statements mismatch at {path}: {len(generated.block.statements)} != {len(expected.block.statements)}")
                return False
            for i, (stmt1, stmt2) in enumerate(zip(generated.block.statements, expected.block.statements)):
                if not TestParser.compare_ast(stmt1, stmt2, path + f".block.statements[{i}]"):
                    return False

        elif isinstance(generated, Block):
            if len(expected.statements) == 1 and isinstance(expected.statements[0], Block):
                return TestParser.compare_ast(generated, expected.statements[0], path)
            else:
                return TestParser.compare_lists(generated.statements, expected.statements, path + ".statements")

        elif isinstance(generated, Input):
            if not TestParser.compare_ast(generated.var_name, expected.var_name, path + ".var_name"):
                return False

        elif isinstance(generated, Comparison):
            if not TestParser.compare_ast(generated.left, expected.left, path + ".left"):
                return False
            if generated.operator != expected.operator:
                print(f"Operator mismatch at {path}.operator: {generated.operator} != {expected.operator}")
                return False
            if not TestParser.compare_ast(generated.right, expected.right, path + ".right"):
                return False

        elif isinstance(generated, BinaryOp):
            if not TestParser.compare_ast(generated.left, expected.left, path + ".left"):
                return False
            if generated.operator != expected.operator:
                print(f"Operator mismatch at {path}.operator: {generated.operator} != {expected.operator}")
                return False
            if not TestParser.compare_ast(generated.right, expected.right, path + ".right"):
                return False
            
        elif isinstance(generated, LogicalOp):
            if not TestParser.compare_ast(generated.left, expected.left, path + ".left"):
                return False
            if generated.operator != expected.operator:
                print(f"Operator mismatch at {path}.operator: {generated.operator} != {expected.operator}")
                return False
            if not TestParser.compare_ast(generated.right, expected.right, path + ".right"):
                return False

        elif isinstance(generated, UnaryOp):
            if generated.operator != expected.operator:
                print(f"Unary operator mismatch at {path}: {generated.operator} != {expected.operator}")
                return False
            if not TestParser.compare_ast(generated.left, expected.left, path + ".operand"):
                return False

        elif isinstance(generated, Integer):
            if generated.value != expected.value:
                print(f"Integer value mismatch at {path}: {generated.value} != {expected.value}")
                return False

        elif isinstance(generated, String):
            if generated.value != expected.value:
                print(f"String value mismatch at {path}: {generated.value} != {expected.value}")
                return False

        else:
            print(f"Unsupported node type at {path}: {type(generated).__name__}")
            return False

        return True

    @staticmethod
    def compare_lists(generated_list, expected_list, path):
        if len(generated_list) != len(expected_list):
            print(f"List length mismatch at {path}: {len(generated_list)} != {len(expected_list)}")
            return False
        for i, (generated, expected) in enumerate(zip(generated_list, expected_list)):
            if not TestParser.compare_ast(generated, expected, path + f"[{i}]"):
                return False
        return True