from Compiler.utils import *
import re

class SemanticAnalyzer:
    def __init__(self, ast):
        self.ast = ast
        self.symbolTable = SymbolTable()
        self.stringCatNodes = []
        
        # context vars
        self.glitchPresent = False
        self.func_name = None
        self.func_params = None
        self.func_return_type = None
        self.inLoopBlock = None

    def analyze(self):
        if error.has_error_occurred():
            print("Parsing errors occurred. Cannot proceed with semantic analysis.")
            return None, None
        
        if self.ast is None or self.symbolTable is None:
            return None, None
        try:
            self.ast.accept(self)
            
        except Exception as e:
            throw(SemanticError(e))
        
        curPassNo = self.ast.node_registry['passNo']
        self.ast.addRef('passNo', (curPassNo+1))
        return self.glitchPresent, self.symbolTable
        
    def visit_program(self, node):
        self.declareBuiltIns()
        try:
            for statement in node.statements:
                if statement is not None:
                    statement.accept(self)
                    
            # We need to evaluate after analysis is complete to ensure correct mutability information for variables.
            for stringCat in self.stringCatNodes:   
                stringCat.accept(self)  
                
        except ExitSignal:
            return 
        except Exception as e:
            throw(SemanticError(f"{red}Semantic analysis error:{reset} {e}"),exit=False)
            return
    
    def visit_block(self, node):
        self.symbolTable.createScope()
        for statement in node.statements:
            if statement is not None:
                statement.accept(self)
        self.symbolTable.exitScope()
        
    def visit_variable(self, node):
        if isinstance(node, VariableDeclaration): 
            self.ast.addRef('varDecl',node)
            if self.symbolTable.inScope(node.name) is not None:
                throw(ReferenceError(f"The name '{str(node.name)}' on line {node.line} is already defined.")) 

            node.value.accept(self)
            data_type = node.evaluateType()
            
            if node.annotation is not None:
                if node.annotation != data_type:
                    if node.annotation == "double" and data_type == "integer":
                        try:
                            var_value = node.value
                            node.value = Double(float(var_value.value))
                            data_type = "double"
                        except Exception as e:
                            throw(CompilationError(f"An error occurred while promoting the int '{str(node.name)}' to a double "),line=node.line)
                    else:    
                        throw(TypeError(f"Variable '{str(node.name)}' expects type '{str(node.annotation)}' but got expression: '{str(node.value)}' of type '{str(data_type)}'"),line=node.line)
                        return
            
            self.symbolTable.add(
                name=node.name,
                symbolType='variable',
                variableData={
                    'value': node.value,
                    'data_type':data_type,
                    'isStatic': self.isStaticEvaluable(node.value),
                    'annotated': True if node.annotation is not None else False
                }
            )

        elif isinstance(node, VariableUpdated):
            self.ast.addRef('varUpdate',node)
            
            var = self.symbolTable.lookup(node.name)
            if var is None:
                throw(ReferenceError(f"Variable '{str(node.name)}' does not exist in this scope"),line=node.line) 
            
            node.value.accept(self)
            data_type = node.evaluateType()
            if data_type == 'invalid': 
                throw(TypeError(f"Could not statically infer the type of variable '{str(node.name)}'. If possible, try adding type hints - you are using glitchy, this is your fault not mine."),line=node.line)
            try:
                symbolTy =  var.get('symbol_type')
                if symbolTy == 'variable':
                    var_data = var.get('variable_data')
                    if var_data.get('annotated') is True:
                        expected_type = var_data.get('data_type') 
                        if expected_type != data_type:
                            throw(TypeError(f"(update) Variable '{str(node.name)}' expects type '{str(expected_type)}' but got expression: '{str(node.value)}' of type '{str(data_type)}'"))
                            return
                                        
                    if self.isStaticEvaluable(node.value):
                        self.symbolTable.update(node.name, data_type, node.value)
                    else:
                        var_data['isStatic'] = False
                        self.symbolTable.update(node.name, data_type, None)  
                elif symbolTy == 'parameter':
                    parm_data = var.get('parameter_data')
                    expected_type = parm_data.get('data_type')
                    if expected_type != data_type:
                        throw(TypeError(f"Parameter '{str(node.name)}' expects type '{str(expected_type)}' but got expression of type '{str(data_type)}'"))
                    
            except Exception as e:
                throw(e,line=node.line)

        elif isinstance(node, VariableReference): 
            self.ast.addRef('varRef',node)
            symbol = self.symbolTable.lookup(node.name)               
            if symbol is None:
                throw(ReferenceError(f"Variable '{str(node.name)}' on line {node.line} has not been defined")) 
            # set type tag so that expression types can be inferred directly without having to lookup value
            if symbol.get('symbol_type') == 'variable':
                var_data = symbol.get('variable_data')
                node.type = var_data.get('data_type','invalid')
                node.value = var_data.get('value', None)
            elif symbol.get('symbol_type') == 'parameter':
                type_str = symbol.get('parameter_data').get('data_type','invalid')
                node.type = type_str
        
    def visit_if(self, node):
        self.ast.addRef('if',node)
        node.comparison.accept(self)
        self.ensureBooleanContext(node.comparison)
        node.block.accept(self)
        
        if node.elifNodes is not None:
            for elif_comparison, elif_block in node.elifNodes:
                elif_comparison.accept(self)
                self.ensureBooleanContext(elif_comparison)
                elif_block.accept(self)
        
        if node.elseBlock is not None:
            node.elseBlock.accept(self)

    def visit_while(self, node):
        self.ast.addRef('while',node)
        node.comparison.accept(self)
        self.ensureBooleanContext(node.comparison)
        self.inLoopBlock = True
        node.block.accept(self)
        self.inLoopBlock = False
            
    def visit_method_call(self, node):
        def validate_call(method_call):
            """ Recursively check method calls starting from the base. """
            if isinstance(method_call.receiver, MethodCall):
                receiver_type = validate_call(method_call.receiver)
            else:
                # base receiver
                method_call.receiver.accept(self)
                receiver_type = method_call.receiver.evaluateType()
            
            method_data = MethodTable.get(receiver_type, method_call.name)
            
            if method_data is None:
                throw(TypeError(f"The method '{str(method_call)}' on line {method_call.line} is not available for type '{str(receiver_type)}'"))

            if len(method_call.args) != method_data['arity']:
                throw(ArgumentError(f"The method '{str(method_call)}' on line {method_call.line} expects {method_data['arity']} argument(s) but got {len(method_call.args)}"))

            for arg, expected_param in zip(method_call.args, method_data['parameters']):
                arg_type = arg.evaluateType()
                if arg_type != expected_param.type:
                    throw(ArgumentError(f"Argument '{str(arg)}' of type '{arg_type}' does not match expected type '{expected_param.type}' for method '{str(method_call)}' on line {method_call.line}"))
            
            method_call.receiverTy = receiver_type
            return method_data['return_type']
        
        node.return_type = validate_call(node)
    
    def visit_function_declaration(self, node):
        self.ast.addRef('funcDecl',node)
        if self.symbolTable.lookup(node.name) is not None:
            throw(ReferenceError(f"The symbol name '{self.name}' on line {node.line} already exists."))
        
        self.symbolTable.add(
            name=node.name, 
            symbolType="function", 
            functionData={
                "parameters": node.parameters,
                "arity": node.arity, 
                "return_type": node.return_type
            }
        )
        
        self.symbolTable.createScope()
        
        for parameter in node.parameters:
            self.symbolTable.add(
                name = parameter.name,
                symbolType = 'parameter',
                parameterData = {
                    'data_type': parameter.type,
                    'function_name': node.name
                }
            )
            
        self.func_name = node.name
        self.func_params = node.parameters
        self.func_return_type = node.return_type

        # validate returns and visit stmts
        has_return_statement = self.validate_return(node.block)
        
        if node.return_type != 'void' and has_return_statement == False:
            throw(ReturnError(f"Not all branches in the function '{node.name}' return correctly"),)
        
        self.symbolTable.exitScope()
        
        self.func_name = None
        self.func_params = None
        self.func_return_type = None

    def visit_return(self, node):
        node.value.accept(self)
        inferred_type = node.evaluateType()
        
        if inferred_type != self.func_return_type:
            if inferred_type == 'null' and self.func_return_type == 'void':
                return
            throw(TypeError(f"Return Type error on line {node.line}. Expected return of type '{self.func_return_type}' for function '{self.func_name}' got: '{inferred_type}' instead."))
    
    def visit_parameter(self, node):
        if not self.symbolTable.lookup(node.name):
            throw(SemanticError(f"Parameter '{str(node.name)}' can not be used in this scope"))
        
    def visit_argument(self, node):
        node.value.accept(self)
        
    def visit_function_call(self, node):
        self.ast.addRef('funcCall', node)
        func_name = node.name
        if func_name == 'typeof':
            node.type = "string"
            return self.evalTypeOf(node)
        if func_name == 'glitch':
            if node.arity != 0:
                throw(ArgumentError(f"Function glitch expects 0 arguments but received {node.arity} arguments"),line=node.line)
            self.glitchPresent = True
            node.replace_self(None) # delete node because there is no concrete implementation of glitch()
            return
        
        symbol = self.symbolTable.lookup(func_name)
        if symbol and 'function_data' in symbol:
            function = symbol['function_data']
        else:
            throw(ReferenceError(f"Incorrect Function Call on line {node.line}. A function with name '{str(node.name)}' does not exist."))
        
        if node.arity != function.get('arity'):
            throw(ArgumentError(f"Function '{func_name}' expects {function['arity']} arguments but received {node.arity} arguments"),line=node.line)
        
        for received_arg, expected_arg in zip(node.args, function.get('parameters')):
            received_arg.accept(self)
            
            if expected_arg.type != 'any': 
                received_arg_type = received_arg.evaluateType()
                if expected_arg.type == 'double' and received_arg_type == 'integer':
                    if isinstance(received_arg.value, Integer):
                        int_ = received_arg.value
                        received_arg.value = Double(float(int_.value))
                        received_arg.cached_type = None
                    elif isinstance(received_arg.value, VariableReference):
                        var = received_arg.value
                        received_arg.value = Double(float(var.value)) 
                        received_arg.cached_type = 'double' 
                
                received_arg_type = received_arg.evaluateType() 
                if received_arg_type != expected_arg.type:
                    throw(TypeError(f"Incorrect Function Call on line {node.line}. Expected type '{expected_arg.type}' for parameter '{expected_arg.name}' got type '{received_arg_type}'"))
                    
        node.type = function.get('return_type', None)

    def visit_comparison(self, node):
        self.ast.addRef('comparison', node)
        self.promoteExprInts(node)
        node.left.accept(self)
        node.right.accept(self)
        self.validateOperation(node)
    
    def visit_binary_op(self, node):
        self.ast.addRef('binOp', node)
        self.promoteExprInts(node)
        isStringCat= self.checkStrcat(node)
        if isStringCat:  # no need to continue 
            return
        node.left.accept(self)
        node.right.accept(self)
        self.validateOperation(node)
    
    def visit_logical_op(self, node):
        self.ast.addRef('logOp', node)
        self.promoteExprInts(node)
        node.left.accept(self)
        node.right.accept(self)
        self.validateOperation(node)
        
    def visit_unary_op(self, node):
        node.left.accept(self)
        self.validateUnary(node.left, node.operator)
    
    def visit_string_cat(self, node):
        self.evalStrCat(node)
    
    def visit_break(self, node):
        pass
    
    def visit_integer(self, node):
        if isinstance(node.value, int) is False:
            throw(CompilationError(f"Invalid data type stored in an integer node: '{type(node.value)}'."))
    
    def visit_double(self, node):
        if isinstance(node.value, float) is False:
            throw(CompilationError(f"Invalid data type stored in an double node: '{type(node.value)}'."))

    def visit_boolean(self, node):
        if node.value not in ['true', 'false']:
            throw(CompilationError(f"Invalid data type stored in an boolean node: '{type(node.value)}'."))

    def visit_string(self, node):
        if isinstance(node.value, str) is False:
            throw(CompilationError(f"Invalid data type stored in an string node: '{type(node.value)}'."))

    def visit_null(self, node):
        pass
    
    # ------------ Helpers ----------------- #
            
    def validateOperation(self, node):
        left, right, operator = node.left, node.right, node.operator
        left_type = left.evaluateType()
        right_type = right.evaluateType()
   
        # Arithmetic
        if operator in ['/', '*', '-', '+', '%', '^']:
            if left_type not in ['integer', 'double'] or right_type not in ['integer', 'double']:
                throw(TypeError(f"Illegal Binary operation on line {left.line}.\n'{str(node)}' with types: '{left_type}' '{operator}' '{right_type}'"))
                
            if operator == '^':
                if left_type != 'double' or right_type != 'double':
                    self.promotePowInts(node)
        
        # Comparisons
        elif operator in ['==', '!=', '<', '<=', '>', '>=']:
            if left_type != right_type:
                if (left_type == 'integer' and right_type == 'double') or (left_type == 'double' and right_type == 'integer'):
                    pass 
                else:
                    throw(TypeError(f"Type mismatch in comparison on line {left.line}. '{str(node)}' with type: '{left_type}' '{operator}' '{right_type}'"))
            elif left_type not in ['integer', 'double', 'string', 'boolean']:
                throw(TypeError(f"Illegal Comparison on line {left.line}.'{str(node)}' with the evaluated types: '{left_type}' '{operator}' '{right_type}'"))
            elif left_type == 'string' and operator not in ['==', '!=']:
                throw(SyntaxError(f"Invalid operator for string comparison on line {left.line}: '{operator}' Only '==' and '!=' are supported for String comparisons"))

            # Handle string comparisons
            self.handleStringComparison(left, right, node)

        # Logical operations
        elif operator in ['&&', '||']:
            if left_type != 'boolean' or right_type != 'boolean':
                throw(TypeError(f"Invalid expression on line {left.line}. Please ensure correct types are being compared: {str(node)} "))
    
    def ensureBooleanContext(self, node):
        expression_type = node.evaluateType()
        if expression_type != 'boolean':
            formattedType = "Invalid" if (expression_type is None) else expression_type
            throw(TypeError(f"Expression on line {node.left.line} does not evaluate to boolean, but to: '{formattedType}'.\n '{str(node)}'"))
    
    def declareBuiltIns(self):
        for func in BuiltInFunctions.getAll():
            self.symbolTable.addGlobalFunction(
                name=func['name'],  
                functionData={
                    'parameters': func['parameters'],  
                    'arity': func['arity'],  
                    'return_type': func['return_type']  
                }
            )

    def isStaticEvaluable(self, value):
        """
        Determines whether a variable's value can be evaluated at compile time, i.e., is Static.
        """
        # Always return True for constant primary values, even inside a loop
        if isinstance(value, Primary):
            return True

        # If inside a loop and the value involves variables, it's not statically evaluable
        if self.inLoopBlock:
            if isinstance(value, VariableReference):
                return False
            
            # For expressions inside a loop, evaluate their components
            elif isinstance(value, Expression):
                if isinstance(value, UnaryOp):
                    return self.isStaticEvaluable(value.left)
                elif isinstance(value, BinaryOp):
                    return self.isStaticEvaluable(value.left) and self.isStaticEvaluable(value.right)
            
            return False

        if isinstance(value, VariableReference):
            symbol = self.symbolTable.lookup(value.name)
            ty =  symbol.get('symbol_type',None)
            if symbol is None or ty is None:
                return False
            
            if ty in ['parameter', 'function']:
                return False
            else:                
                var_data = symbol.get('variable_data', {})
                return var_data.get('isStatic', False)
        
        elif isinstance(value, Expression):
            if isinstance(value, UnaryOp):
                return self.isStaticEvaluable(value.left)
            elif isinstance(value, BinaryOp):
                return self.isStaticEvaluable(value.left) and self.isStaticEvaluable(value.right)
        
        # catch all
        return False
    
    def validateUnary(self, left, operator):
        operand_type = left.evaluateType()

        if operator == '!':
            if operand_type != 'boolean':
                throw(SemanticError(f"Unary Operation on line {left.line}: '{str(operator)+str(left)}' does not have a boolean operand, but one of: '{operand_type}'"))
        elif operator == '-' or operator == '+':
            if operand_type not in ['integer', 'double']:
                throw(SemanticError(f"Unary Operation on line {left.line}: '{str(operator)+str(left)}' does not have a numeric operand, but one of type: '{operand_type}'"))

        else:
            throw(SemanticError(f"Invalid Unary Operation on {left.line}: '{str(operator)+str(left)}' Invalid operator: '{operator}'" ))

    def checkStrcat(self, node):
        """ 
        Decides wether or not a BinaryOp is a String concatenation. 
        if it is, calls the appropriate  method, that will transform to a StringCat node and attempt to evaluate it
        """
        left, right, operator = node.left, node.right, node.operator
        
        # we dont want to accept binaryOps since that will start processing as an Arithmetic op
        if isinstance(node.left, BinaryOp) is False:
            left.accept(self)
        if isinstance(node.right, BinaryOp) is False:
            right.accept(self)
            
        left_type = left.evaluateType()
        right_type = right.evaluateType()
        
        if left_type == 'string' or right_type == 'string':
            strcat_node = self.transformStrcat(node)
            if isinstance(strcat_node, StringCat):
                return True
        return False
            
    def transformStrcat(self, node):
        """
        Validates and transforms a BinaryOp node into a StringCat node.
        If possible we completely evaluate it. if not, we defer to runtime
        This is not done in the parser since all type info is not available.
        """
        if isinstance(node, BinaryOp):
            strings = self._collectStrings(node)
            string_cat_node = StringCat(strings=strings, line=node.line)

            node.replace_self(string_cat_node)
            node.transformed = True
            
            # For later evaluation
            self.stringCatNodes.append(string_cat_node)
            
            return string_cat_node
        else:
            return node

    def _collectStrings(self, node):
        """
        Recursively collect all string literals and static variables for concatenation
        from a BinaryOp tree into a single list. If we find a value that is non-static we defer to runtime
        """
        strings = []

        def collect(node):
            is_string_cat = isinstance(node, BinaryOp) and node.operator == '+' and node.evaluateType() == 'string'
            if not is_string_cat:  # accepting a binaryOp wll lead to processing like arithmetic 
                node.accept(self)
            if is_string_cat:
                collect(node.left)
                collect(node.right)
            elif node.evaluateType() in ['string','integer','double','boolean','null']:
                strings.append(node)
            else:
                throw(TypeError(f"Illegal Expression in String concatenation: {node}  with types:'{node.evaluateType()}' '+' '{node.evaluateType()}'"))

        collect(node)
        return strings
    
    def evalStrCat(self, node):
        """ Attempts to evaluated a string concatenation. defers otherwise """
        if node.visited:
            return
        node.visited = True
        evaluated_strings = []
        buffer = [] 
        fully_evaluated = True  

        for expr in node.strings:
            if isinstance(expr, VariableReference) or isinstance(expr, FunctionCall):
                if isinstance(expr, VariableReference) and expr.value is not None:
                    isStatic = self.symbolTable.isStatic(expr.name, expr.scope)
                    evaluated_string = False
                    if isStatic:
                        evaluated_string = self._opToString(expr.value)
                    if evaluated_string is False:
                        fully_evaluated = False  # Needs runtime evaluation
                        if buffer:
                            evaluated_strings.append(''.join(buffer))  
                            buffer = []
                        evaluated_strings.append(expr)  
                    else:
                        buffer.append(evaluated_string)
                else:
                    fully_evaluated = False  # Needs runtime evaluation
                    if buffer:
                        evaluated_strings.append(''.join(buffer))  
                        buffer = []
                    evaluated_strings.append(expr) 
            elif isinstance(expr, Primary):
                evaluated_string = self._opToString(expr)
                buffer.append(evaluated_string)
            elif isinstance(expr, Expression):
                if isinstance(expr, UnaryOp):
                    evaluated_expr = self._evaluateUnary(expr)
                else:
                    evaluated_expr = self._evaluateExpression(expr)
                if evaluated_expr is None:
                    fully_evaluated = False
                    if buffer:
                        evaluated_strings.append(''.join(buffer))  
                        buffer = []
                    evaluated_strings.append(expr)  # Runtime evaluation of BinaryOp
                else:
                    buffer.append(evaluated_expr)  # Append the evaluated expression

            else:
                throw(TypeError(f"Unsupported type in string concatenation on line {node.line}: {type(expr).__name__}"))

        if buffer:
            evaluated_strings.append(''.join(buffer))

        if fully_evaluated:
            node.evaluated = String(''.join(evaluated_strings))
            node.strings = [node.evaluated]  
        else:
            node.evaluated = None
            node.strings = evaluated_strings  # Keep the partially evaluated list

    def _opToString(self, operand):
        """Convert a literal operand to string using repr() if it's already one"""
        if operand is None:
            return False
        if operand.evaluateType() == 'string':
                if isinstance(operand, String):
                    return operand.value
                else:
                    return False
        elif operand.evaluateType() in ['integer', 'double', 'boolean', 'null']:
            if isinstance(operand, Primary):
                return repr(operand.value)
            else:
                return False

    def _evaluateExpression(self, expr):
        """ Evaluates static expressions for binary operations and converts the result to a string. Returns None to pass to runtime """
        try:
            operators = {
                '+': lambda x, y: x + y,
                '-': lambda x, y: x - y,
                '*': lambda x, y: x * y,
                '/': lambda x, y: x / y,
                '%': lambda x, y: x % y,
                '==': lambda x, y: x == y,
                '!=': lambda x, y: x != y,
                '>=': lambda x, y: x >= y,
                '<=': lambda x, y: x <= y,
                '>': lambda x, y: x > y,
                '<': lambda x, y: x < y,
            }
            
            def evaluate_node(node):
                if isinstance(node, FunctionCall) or isinstance(node, MethodCall):
                        return None 
                elif isinstance(node, VariableReference):
                    if self.symbolTable.isStatic(node.name) is False:
                        return None 
                    return node.value
                elif hasattr(node, 'left') and hasattr(node, 'right'):
                    left_val = evaluate_node(node.left)
                    right_val = evaluate_node(node.right)
                    if left_val is not None and right_val is not None:
                        op_func = operators.get(expr.operator)
                        if op_func:
                            return str(op_func(left_val, right_val))
                        return None 
                    else:
                        return None 
                return node.value
            
            return evaluate_node(expr)
        except ExitSignal:
            raise ExitSignal
        except Exception:
            return None

    def _evaluateUnary(self, expr):
        """ Evaluates unary operations for static expressions and converts the result to a string. Returns False to pass to runtime """
        try:
            def evaluate_node(node):
                if isinstance(node, VariableReference):
                    if self.symbolTable.isStatic(node.name) is False:
                        return None 
                    return node.value
                elif hasattr(node, 'left'):
                    left_val = evaluate_node(node.left)
                    if left_val is not None:
                        if expr.operator == '+':
                            return str(+left_val)
                        elif expr.operator == '-':
                            return str(-left_val)
                        else:
                            return None 
                    else:
                        return None 
                return node.value
            return evaluate_node(expr)
        except ExitSignal:
            raise ExitSignal
        except Exception:
            return None

    def evalTypeOf(self, node):
        """ evaluates a typeOf function call to a type string and then transforms it to a String node"""
        
        if node.arity != 1:
            throw(ArgumentError(f"The function 'typeof' on line {node.line} expects 1 argument but got {len(node.args)}"))
        
        eval_value = node.args[0].value
        eval_value.accept(self)
        ty = node.args[0].value.evaluateType()
        
        if ty == 'invalid':
            if isinstance(eval_value, VariableReference):
                throw(Error(f"An error occurred during the evaluation of the typeOf call on line {node.line}: '{str(eval_value.value)}'"))
            else:
                throw(Error(f"An error occurred during the evaluation of the typeOf call on line {node.line}: '{str(eval_value)}'"))

        # we flag it as a ty_string so we can do special comparisons like: 'int' == 'integer' => true
        node.replace_with(String(ty,True))
     
    def promoteExprInts(self, node, expr_type=None):
        """
        Promote integers in exprs that evaluate to double. Will not work on variables, runtime will convert these cases
        """

        expr_type = expr_type or node.evaluateType()  # Pass to recursive calls so they know the type of overall expr
        left_type = node.left.evaluateType()
        right_type = node.right.evaluateType()
    
        if expr_type == 'double':
            if left_type == 'integer':
                if isinstance(node.left, Integer):
                    node.left = Double(float(node.left.value))
                else:
                    self.promoteExprInts(node.left, expr_type)  
                node.cached_type = None

            if right_type == 'integer':
                if isinstance(node.right, Integer):
                    node.right = Double(float(node.right.value))
                else:
                    self.promoteExprInts(node.right, expr_type)  
                node.cached_type = None
    
    def promotePowInts(self, node, expr_type=None):
        """Promotes all ints to doubles in exponentiation ('^') exprs. V """
        
        if expr_type == 'double' or isinstance(node, VariableReference):
            return
        
        expr_type = expr_type or node.evaluateType()
        left_type = node.left.evaluateType()
        right_type = node.right.evaluateType()

        if expr_type == 'integer':
            if isinstance(node, BinaryOp):
                if left_type == 'integer':
                    if isinstance(node.left, Integer):
                        node.left = Double(float(node.left.value))
                    else:
                        self.promotePowInts(node.left, expr_type)  
                    node.cached_type = None
                    
                if right_type == 'integer':
                    if isinstance(node.right, Integer):
                        node.right = Double(float(node.right.value))
                    else:
                        self.promotePowInts(node.right, expr_type)  
                    node.cached_type = None
        else:
            throw(TypeError(f"Invalid type in exponentiation on line {node.line}: '{str(node)}' with types'{left_type}' '^' '{right_type}'"))
    
    def validateTyStr(self, type_string):
        """
        When given the first three chars (or more) of a type string will return the full form. 
        all these inputs will return the same ty_str
        int/inte/integ/intege/integer => 'integer'
        bool/boole/boolea/boolean => 'boolean'
        str/stri/strin/string => 'string'
        double => 'double'
        """
        type_pattern = r"""
            \b(?:
                (?P<int_type>int(?:eger|ege|eg|e)?)   |  # Matches int, inte, integ, intege, integer
                (?P<double_type>double)                |  # Matches double
                (?P<str_type>str(?:ing|in|i)?)       |  # Matches str, stri, strin, string
                (?P<bool_type>bool(?:ean|ea|e)?)        # Matches bool, boole, boolea, boolean
            )\b
        """
        match = re.search(type_pattern, type_string, re.VERBOSE)
        type_tag = 'invalid'
        
        if match is not None:
            if match.group("int_type"):
                type_tag = 'integer'
            elif match.group("double_type"):
                type_tag= 'double'
            elif match.group("str_type"):
                type_tag = 'string'
            elif match.group("bool_type"):
                type_tag = 'boolean'      
        
        return type_tag    
    
    def handleStringComparison(self, left, right, node):
        """Handle string comparisons, including special typeof comparisons"""
        # Check if left or right is a FunctionCall for typeof
        if (isinstance(left, FunctionCall) and left.name == 'typeof') or \
        (isinstance(right, FunctionCall) and right.name == 'typeof'):
            throw(CompilationError(f"An error occurred during the evaluation of the function call: {str(left if isinstance(left, FunctionCall) else right)}"))
        
        # Check if left or right is a VariableReference
        if isinstance(left, VariableReference):
            left = left.value if left.value is not None else left  # Safely resolve value
        if isinstance(right, VariableReference):
            right = right.value if right.value is not None else right  # Safely resolve value
        
        # Check for isTypeStr attributes
        isTypeOf = hasattr(left, "isTypeStr") and left.isTypeStr or \
                hasattr(right, "isTypeStr") and right.isTypeStr

        if isTypeOf:
            left_ty_str = self.validateTyStr(left.value)
            right_ty_str = self.validateTyStr(right.value)
            if left_ty_str != 'invalid' or right_ty_str != 'invalid':
                left.value = left_ty_str
                right.value = right_ty_str        
                
            
    def validate_return(self, block):
        """
        Helper to validate returns in a function body. traverses the block of statements once, performing both the visiting of each node (via accept)
        and ensuring return statements are correctly placed.
        """
        has_return = False
        for stmt in block.statements:
            stmt.accept(self)  
            if isinstance(stmt, Return):
                has_return = True
            elif isinstance(stmt, If):
                if_returns = self.validate_if_return(stmt)
                has_return = has_return or if_returns
            elif isinstance(stmt, FunctionCall):
                if stmt.name == self.func_name:
                    has_return = True
        return has_return

    def validate_if_return(self, node):
        """
        Checks if an `if-elif-else` statement ensures all paths have a return statement.
        """
        if_block_has_return = self.validate_return(node.block)
        elif_blocks_have_return = all(self.validate_return(elif_block_node) for _, elif_block_node in node.elifNodes)

        if node.elseBlock is not None:
            else_block_has_return = self.validate_return(node.elseBlock)
        else:
            else_block_has_return = False  
            
        if else_block_has_return:
            return True
        if if_block_has_return or elif_blocks_have_return:
            return False 

        throw(ReturnError(f"Not all paths in the if-elif-else block return in function '{self.func_name}'."))
          