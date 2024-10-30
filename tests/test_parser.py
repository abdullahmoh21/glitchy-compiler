import unittest
import sys
import os
from Compiler.Lexer import *
from Compiler.Parser import *
from Compiler.utils import *

class TestParser(unittest.TestCase):
    def test_simple_set_and_print(self):
        source_code = '''
        set x = 42
        print("Hello, world")
        '''
        expected_ast = Program([
            VariableDeclaration("x", Integer(42), 2),
            FunctionCall('print', [Argument(String("Hello, world"))], 3)
        ])
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
                    FunctionCall('print',[Argument(String("x is ten"))],line=4)
                ]),
                3
            )
        ])
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
                    FunctionCall('print',[Argument(String("x is greater than ten"))],4 )
                ]),
                elifNodes=[
                    (
                        Comparison(VariableReference("x", 5), "<", Integer(10, 5), 5),
                        Block([
                            FunctionCall('print',[Argument(String("x is less than ten"))],6 )
                        ])
                    )
                ],
                elseBlock=Block([
                    FunctionCall('print',[Argument(String("x is ten"))],8 )
                ]),
                line=3
            )
        ])

        
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
                                    FunctionCall('print',[Argument(String("x is ten"))], 6)
                                ]),
                                5
                            )
                        ]),
                        4
                    )
                ]),
                3
            )
        ])
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
        ])
        self.run_test(source_code, expected_ast)

    def test_input_statement(self):
        source_code = '''
        set foo = input()
        print(foo)
        '''
        expected_ast = Program([
            VariableDeclaration('foo',
                FunctionCall('input',[], line=2)
            ),
            FunctionCall('print',[Argument((VariableReference("foo")))], 3)
        ])
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
        ])
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
        ])

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
        ])

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
        ])

        self.run_test(source_code, expected_ast)

    def test_deeply_nested_parentheses(self):
        source_code = '''
        set result = ((((x + 1) * (y - 2)) / 3) == z) && !(a || b)
        '''
        
        expected_ast = Program([
            VariableDeclaration(
                name='result',
                value=LogicalOp(
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
                value=BinaryOp(
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
        ])

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
            VariableDeclaration("x", Integer(1), line=2),
            If(
                Comparison(VariableReference("x", 3), "==", Integer(1, 3), 3),
                Block([
                    VariableDeclaration("y", Integer(2), line=4),
                    If(
                        Comparison(VariableReference("y", 5), "==", Integer(2, 5), 5),
                        Block([
                            FunctionCall('print',[Argument(String("y is two"))], 6)
                        ]),
                        5
                    )
                ]),
                3
            )
        ])
        self.run_test(source_code, expected_ast)

    def test_expression_with_parentheses(self):
        source_code = '''
        set result = (a + (b * c) - d) / e
        '''
        expected_ast = Program([
            VariableDeclaration("result", 
                BinaryOp(
                    BinaryOp(
                        VariableReference("a", 2),
                        "+",
                        BinaryOp(
                            BinaryOp(
                                VariableReference("b", 2),
                                "*",
                                VariableReference("c", 2),
                                2
                            ),
                            "-",
                            VariableReference("d", 2),
                            2
                        ),
                        2
                    ),
                    "/",
                    VariableReference("e", 2),
                    2
                ), 
                2
            )
        ])

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
        ])
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
                        FunctionCall('print',[Argument(String("Looping"))], 3),
                        VariableUpdated("i",BinaryOp(VariableReference("i", 3), "+", Integer(2, 3), 3), 3)  # Increment
                    ]),
                    2
                )
            ])
        ])
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
                        FunctionCall('print',[Argument(String("Looping"))], 3),
                        VariableUpdated("i", BinaryOp(VariableReference("i", 3), "+", Integer(1, 3), 3), 3)  # Increment
                    ]),
                    2
                )
            ])
        ])
        self.run_test(source_code, expected_ast)

    def test_function_decl(self):
        source_code = """
        function int myFunction(a:int, b:string) {
            set x:int = 10
            set y:string = "hello world"
        }
        """
        
        expected_ast = Program([
                FunctionDeclaration(
                name="myFunction",
                return_type="integer",
                parameters=[
                    Parameter(name="a", type="integer"),
                    Parameter(name="b", type="string")
                ],
                block=Block(statements=[
                    VariableDeclaration(name="x", value=Integer(10), annotation="integer"),
                    VariableDeclaration(name="y", value=String("hello world"), annotation="string")
                ])
            )
        ])
        
        self.run_test(source_code, expected_ast)
        
    def test_function_call(self):
        pass
    
    def test_multiple_assignment_with_annotation(self):
        source_code = """
        set a, b, c, d:int = 10 // int annotation will apply to all
        """
        
        expected_ast = Program([
                VariableDeclaration(name="a", value=Integer(10), annotation="integer"),
                VariableDeclaration(name="b", value=Integer(10), annotation="integer"),
                VariableDeclaration(name="c", value=Integer(10), annotation="integer"),
                VariableDeclaration(name="d", value=Integer(10), annotation="integer"),
        ])
        
        self.run_test(source_code, expected_ast)

    def test_multiple_assignment_without_annotation(self):
        source_code = """
        set x, y, z, a = 10
        """
        
        expected_ast = Program([
            VariableDeclaration(name="x", value=Integer(10)),
            VariableDeclaration(name="y", value=Integer(10)),
            VariableDeclaration(name="z", value=Integer(10)),
            VariableDeclaration(name="a", value=Integer(10))
        ])
        
        self.run_test(source_code, expected_ast)
       
    def run_test(self, source_code, expected_ast):
        lexer = Lexer(source_code)
        parser = Parser(lexer)
        generated_ast = parser.parse()
        if not TestParser.compare_ast(generated_ast, expected_ast):
            self.fail("\n[ERROR] Generated AST does not match expected AST\n")
    
    @staticmethod
    def compare_ast(generated, expected, path=""):
        if type(generated) != type(expected):
            print(f"Type mismatch at {path}: {type(generated).__name__} != {type(expected).__name__}")
            return False

        if isinstance(generated, Program):
            if len(generated.statements) != len(expected.statements):
                print(f"Number of statements mismatch at {path}: {len(generated.statements)} != {len(expected.statements)}")
                return False
            for i, (stmt1, stmt2) in enumerate(zip(generated.statements, expected.statements)):
                if not TestParser.compare_ast(stmt1, stmt2, path + f".statements[{i}]"):
                    return False

        elif isinstance(generated, VariableDeclaration):
            if generated.name != expected.name:
                print(f"VariableDeclaration name mismatch at {path}: '{generated.name}' != '{expected.name}'")
                return False
            
            if generated.annotation != expected.annotation:
                print(f"VariableDeclaration type annotation mismatch at {path}: {generated.annotation} != {expected.annotation}")
                return False
            
            if not TestParser.compare_ast(generated.value, expected.value, path + ".value"):
                print(f"VariableDeclaration's value mismatch at {path}: {generated.value} != {expected.value}")
                return False

        elif isinstance(generated, VariableUpdated):
            if generated.name != expected.name:
                print(f"VariableUpdated name mismatch at {path}: '{generated.name}' != '{expected.name}'")
                return False
            if not TestParser.compare_ast(generated.value, expected.value, path + ".value"):
                print(f"VariableUpdated's value mismatch at {path}: {generated.value} != {expected.value}")
                return False

        elif isinstance(generated, VariableReference):
            if generated.name != expected.name:
                print(f"VariableReference name mismatch at {path}: '{generated.name}' != '{expected.name}'")
                return False

        elif isinstance(generated, FunctionDeclaration):
            if generated.name != expected.name:
                print(f"FunctionDeclaration name mismatch at {path}: '{generated.name}' != '{expected.name}'")
                return False
            if generated.return_type != expected.return_type:
                print(f"FunctionDeclaration return type mismatch at {path}: {generated.return_type} != {expected.return_type}")
                return False
            
            if not TestParser.compare_lists(generated.parameters, expected.parameters, path + ".parameters"):
                print(f"FunctionDeclaration parameter mismatch at {path}: {generated.parameters} != {expected.parameters}")
                return False
            
            if not TestParser.compare_lists(generated.block.statements, expected.block.statements, path + ".block"):
                print(f"FunctionDeclaration block mismatch at {path}: {generated.parameters} != {expected.parameters}")
                return False
        
        elif isinstance(generated, Parameter):
            if generated.name != expected.name:
                print(f"Parameter name mismatch at {path}: '{generated.name}' != '{expected.name}'")
                return False
            
            if generated.type != expected.type:
                print(f"Parameter type mismatch at {path}: {generated.type} != {expected.type}")
                return False
            
        elif isinstance(generated, FunctionCall):
            if generated.name != expected.name:
                print(f"FunctionCall name mismatch at {path}: '{generated.name}' != '{expected.name}'")
                return False
            
            if not TestParser.compare_lists(generated.args,expected.args, path+".functionCall"):
                print(f"FunctionCall argument mismatch at {path}: {generated.args} != {expected.args}")
                return False

        elif isinstance(generated, Argument):
            if generated.evaluateType() != expected.evaluateType():
                print(f"Argument type mismatch at {path}: {generated.evaluateType()} != {expected.evaluateType()}")
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
            if not TestParser.compare_ast(generated.comparison, expected.comparison, path + ".comparison"):
                return False
            if len(generated.block.statements) != len(expected.block.statements):
                print(f"While statement block number of statements mismatch at {path}: {len(generated.block.statements)} != {len(expected.block.statements)}")
                return False
            for i, (stmt1, stmt2) in enumerate(zip(generated.block.statements, expected.block.statements)):
                if not TestParser.compare_ast(stmt1, stmt2, path + f".block.statements[{i}]"):
                    return False

        elif isinstance(generated, Block):
            return TestParser.compare_lists(generated.statements, expected.statements, path + ".statements")

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

        elif isinstance(generated, Double):
            if generated.value != expected.value:
                print(f"Double value mismatch at {path}: {generated.value} != {expected.value}")
                return False

        elif isinstance(generated, Boolean):
            if generated.value != expected.value:
                print(f"Boolean value mismatch at {path}: {generated.value} != {expected.value}")
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