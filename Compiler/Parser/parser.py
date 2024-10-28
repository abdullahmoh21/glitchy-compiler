import sys
import re
from Compiler.Lexer import *
from Compiler.utils import *

class Parser:
    def __init__(self, lexer):
        self.lexer = lexer
        self.lineNumber = 1
        self.currentToken = None
        self.peekToken = None
        self.inFunctionBlock = False
        self.inLoopBlock = False
        
        # Initialize currentToken and peekToken
        self.nextToken()    
        self.nextToken()    

    # -------------- General Helper Methods ----------------- #
    
    def checkToken(self, *types):
        """ 
        Will check if the current token is of any of the specified types.
        Supports multiple token types and variable arguments.
        """
        if self.currentToken is None:
            return False
        return self.currentToken.type in types

    def checkPeek(self, *types):
        """ 
        Will check if the NEXT token is of any of the specified types.
        Supports multiple token types and variable arguments.
        """
        if self.peekToken is None:
            return False
        return self.peekToken.type in types

    def match(self, *types, errorMsg=None):
        """
        Will consume the current token if it is of any of the specified types. Otherwise, report an error.
        """
        if not self.checkToken(*types):
            if errorMsg is None:
                expected_types = ", ".join([t.name for t in types])
                errorMsg = f"Expected one of: {expected_types}, got '{self.currentToken.value}' (type: {self.currentToken.type.name})"
            report(errorMsg, line=self.lineNumber, type_="Syntax")
        self.nextToken()
        
    def nextToken(self):
        # To ensure tokens don't loop back to the start since we are directly connected to lexer
        if self.currentToken and self.checkToken(TokenType.EOF):
            return self.currentToken
        
        self.currentToken = self.peekToken
        self.peekToken = self.lexer.getToken()
        
        if self.currentToken and self.currentToken.type == TokenType.NEWLINE:
            self.lineNumber += 1
    
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
    
    def panic(self):
        sync_points = {TokenType.RBRACE,TokenType.LBRACE, TokenType.IF, TokenType.WHILE, TokenType.FOR, TokenType.SET, TokenType.EOF}

        while not self.checkToken(*sync_points):
            self.nextToken()

        self.nl()

        if self.checkToken(TokenType.EOF):
            raise ExitSignal()
            
        if self.checkToken(TokenType.RBRACE):
            self.match(TokenType.RBRACE)
        elif self.checkToken(TokenType.NEWLINE):
            self.nextToken() 
        else:
            while not self.checkToken(*sync_points):
                self.nextToken()
            
            if self.checkToken(TokenType.NEWLINE):
                self.nextToken()  

    def nl(self):
        """ Continues to remove whitespace until another token type is found """
        if self.checkToken(TokenType.NEWLINE):
            while self.checkToken(TokenType.NEWLINE):
                self.nextToken()
    
    def isComparisonOperator(self):
        return self.checkToken(TokenType.GT) or self.checkToken(TokenType.GTEQ) or \
            self.checkToken(TokenType.LT) or self.checkToken(TokenType.LTEQ) 
    
    def reportUnknownTok(self):
        errMsgs = {
            TokenType.RETURN: "Cannot return main function. Return statements are only allowed inside a function body. ",
            TokenType.RETURN: "Break statements are only allowed inside a loop body. ",
            TokenType.LBRACE: "Unexpected '{'. Did you forget to close a previous block or add a semicolon?",
            TokenType.RBRACE: "Unexpected '}'. Did you forget to open a block or are you closing it too early?",
            TokenType.LPAREN: "Unexpected '('. This might indicate a missing operator or incorrect function/method call.",
            TokenType.RPAREN: "Unexpected ')'. You may be missing an opening parenthesis or have unmatched parentheses.",
            TokenType.SEMICOLON: "Unexpected ';'. You dont need to end statements with semicolons.",
            TokenType.COMMA: "Unexpected ','. Ensure that you're using in correct context.",
            TokenType.IF: "Unexpected 'if'. This keyword is only valid at the beginning of an if-else statement.",
            TokenType.ELSE: "Unexpected 'else'. 'else' must follow an 'if' block or an 'elif' block.",
            TokenType.ELIF: "Unexpected 'elif'. 'elif' must follow an 'if' block or another 'elif' block.",
            TokenType.WHILE: "Unexpected 'while'. This keyword is only valid at the beginning of a while loop statement.",
            TokenType.EQ: "Unexpected '='. You might be trying to assign a value outside a proper context.",
            TokenType.EQEQ: "Unexpected '=='. This comparison operator might be used outside a valid comparison context.",
            TokenType.PLUS: "Unexpected '+'. Make sure you're using it in a valid arithmetic or concatenation context.",
            TokenType.MINUS: "Unexpected '-'. Make sure you're using it in a valid arithmetic or subtraction context.",
            TokenType.ASTERISK: "Unexpected '*'. Ensure you're using the multiplication operator in a valid context.",
            TokenType.SLASH: "Unexpected '/'. This division operator might be out of place.",
            TokenType.AND: "Unexpected '&&'. Logical AND should be used in a condition, not as a standalone token.",
            TokenType.OR: "Unexpected '||'. Logical OR should be used in a condition, not as a standalone token.",
            TokenType.NOT: "Unexpected '!'. The NOT operator should be followed by a condition or a boolean value.",
            TokenType.INCREMENT: "Unexpected '++'. Ensure that '++' is used as a standalone statement or within an expression.",
            TokenType.DECREMENT: "Unexpected '--'. Ensure that '--' is used as a standalone statement or within an expression.",
        }
        
        if self.currentToken.type in errMsgs:
            report(
                message=errMsgs[self.currentToken.type],
                type_="Syntax", 
                line=self.lineNumber
            )
            return True
    
    def identSuggestions(self):
        ident_name = {
            "print" : "Did you mean to call the print function? Please dont forget the enclosing parenthesis: 'print(...)'",
            "input" : "Did you mean to call the input function? Please dont forget the enclosing parenthesis: 'input(...)"
        }
        
        if self.checkToken(TokenType.IDENTIFIER) and self.currentToken.value in ident_name:
            report(
                message=ident_name[self.currentToken.value],
                type_="Syntax", 
                line=self.lineNumber
            )
            return True
    
    # ------------ Recursive Descent Parsing ----------------- #
    
    def parse(self):
        statements = []

        try:
            while not self.checkToken(TokenType.EOF):
                stmt = self.statement()
                if stmt is not None:     
                    if isinstance(stmt, list):
                        statements.extend(stmt)
                    else:
                        statements.append(stmt)
        except ExitSignal:
            return
        except Exception as e:
            throw(ParsingError(f"An unknown error occurred during parsing: {e}"),exit=False)
        
        return Program(statements)

    def statement(self):
        """ Parses all statements returns one node or an array of nodes """
        node = None
        try:
                        
            if self.checkToken(TokenType.IF):
                self.match(TokenType.IF)
                ifLine = self.lineNumber
                self.match(TokenType.LPAREN, errorMsg="if conditions must be enclosed within parenthesis: '(' 'condition' ')'")
                comparison_node = self.expression()    
                self.match(TokenType.RPAREN, errorMsg="No closing parenthesis ')' for if statement found.")
                if_block_node = self.block()

                else_block_node = None
                elif_nodes = []
                
                self.nl()   
                
                while self.checkToken(TokenType.ELIF):
                    self.match(TokenType.ELIF)
                    self.match(TokenType.LPAREN, errorMsg="elif conditions must be enclosed within parenthesis: '(' 'condition' ')'")
                    elif_comparison_node = self.expression()
                    self.match(TokenType.RPAREN, errorMsg="No closing parenthesis ')' for elif condition found.")
                    elif_block_node = self.block()
                    elif_nodes.append((elif_comparison_node, elif_block_node))
                    
                    if(self.checkToken(TokenType.NEWLINE)):
                        self.nl()

                self.nl()   
                
                if self.checkToken(TokenType.ELSE):
                    self.match(TokenType.ELSE)
                    else_block_node = self.block()
                
                base_args = {
                    'comparison': comparison_node,
                    'block': if_block_node,
                    'line': ifLine
                }
                # Add optional arguments conditionally
                if elif_nodes:
                    base_args['elifNodes'] = elif_nodes

                if else_block_node:
                    base_args['elseBlock'] = else_block_node

                node = If(**base_args)

            elif self.checkToken(TokenType.FUNCTION):
                self.match(TokenType.FUNCTION)
                return_type = self.currentToken.value
                self.match(TokenType.IDENTIFIER)
                return_type_tag = self.validateTyStr(return_type) if return_type != 'void' else "void"
                function_name = self.currentToken.value
                self.match(TokenType.IDENTIFIER)
                self.match(TokenType.LPAREN, errorMsg="Function declarations must have parenthesis '(' after the function name.")
                parameters = []
                param_err = False
                while not self.checkToken(TokenType.RPAREN):
                    parameter_name = self.currentToken.value
                    self.nextToken()
                    if not self.checkToken(TokenType.COLON):
                        report(f"Missing token ':' Parameters must be in format 'name' ':' 'type'",type_="Syntax",line=self.lineNumber)
                        param_err = True
                        break
                    self.nextToken()
                    param_type = self.currentToken.value
                    param_type_tag = self.validateTyStr(param_type)
                    self.nextToken()
                    parameters.append(Parameter(parameter_name, param_type_tag))
                    if self.checkToken(TokenType.COMMA): #trailing comma's allowed
                        self.match(TokenType.COMMA)
                if param_err:
                    self.panic()
                else:
                    self.match(TokenType.RPAREN, errorMsg="No enclosing parenthesis ')' found for function declaration")
                
                self.inFunctionBlock = True
                function_body = self.block()
                self.inFunctionBlock = False
                node = FunctionDeclaration(function_name, return_type_tag, parameters, function_body, self.lineNumber)
            
            elif self.checkToken(TokenType.RETURN):
                if self.inFunctionBlock == False:
                    report("Return statements are only allowed inside a functions body",type_="Syntax",line=self.lineNumber)
                    self.panic()
                    
                self.nextToken()
                if not self.checkToken(TokenType.NEWLINE):
                    returnVal = self.expression()
                    node = Return(returnVal, self.lineNumber)
                else:
                    node = Return(Null(),self.lineNumber)
            
            elif self.checkToken(TokenType.BREAK):
                if self.inLoopBlock == False:
                    report("Break statements are only allowed inside a functions body",type_="Syntax",line=self.lineNumber)
                else:
                    self.nextToken()
                    node = Break(self.lineNumber)
            
            elif self.checkToken(TokenType.WHILE):
                self.match(TokenType.WHILE)
                self.match(TokenType.LPAREN, errorMsg="While conditions must be enclosed within parenthesis: '(' 'condition' ')'")
                comparison_node = self.expression()   # parse an expression rn, will validate it later
                self.match(TokenType.RPAREN, errorMsg="No closing parenthesis ')' for while condition found.")
                self.inLoopBlock = True
                block_node = self.block()
                self.inLoopBlock = False
                node = While(comparison_node, block_node, self.lineNumber)
            
            elif self.checkToken(TokenType.FOR):
                self.match(TokenType.FOR)
                self.match(TokenType.LPAREN, errorMsg="Missing '(' after 'for' ")

                if self.checkToken(TokenType.SET):      # allow "set i = 0"
                    self.nextToken()
                var_name = self.currentToken.value
                self.match(TokenType.IDENTIFIER, errorMsg=f"Expected counter variable, got: {var_name}")
                self.match(TokenType.EQ,errorMsg="Missing '=' token in for loop's counter initialization")
                initialCount = self.expression()
                self.match(TokenType.SEMICOLON, errorMsg=f"For loops Counter initialization should be followed by a semicolon, got: {self.currentToken.value}")

                comparison_node = self.expression()   # parse an expression rn, will validate it later
                self.match(TokenType.SEMICOLON, errorMsg="For loop's Comparison should be followed by a semicolon, got: {self.currentToken.value}")

                increment = None
                if self.checkToken(TokenType.IDENTIFIER):
                    self.nextToken()
                    if self.checkToken(TokenType.INCREMENT):
                        increment = self.handleIncr(var_name)
                    elif self.checkToken(TokenType.DECREMENT):
                        increment = self.handleDecr(var_name)
                    else:
                        increment = self.handleVarAssign(var_name)
                else:
                    report(f"Expected increment/decrement to start with variable '{var_name}' got: '{self.currentToken.value}' instead",type_="Syntax",line=self.lineNumber)
                if isinstance(increment, list) or not isinstance(increment, VariableUpdated):
                    report(f"Expected increment/decrement expression, got '{repr(increment)} '", line=self.lineNumber, type_="Syntax")
                    self.panic()
                    
                self.match(TokenType.RPAREN, errorMsg="Missing closing parenthesis ')' in For loop")
                
                self.inLoopBlock = True
                while_body = self.block(appendNode=increment)
                self.inLoopBlock = False
                
                # Desugar to a while loop
                initialization_node = VariableDeclaration(var_name, initialCount, self.lineNumber)
                initialization_node.forLoopCounter = True
                node = Block([initialization_node, While(comparison_node, while_body, self.lineNumber)])
                
            elif self.checkToken(TokenType.SET):
                self.match(TokenType.SET)
                var_name = self.currentToken.value
                self.match(TokenType.IDENTIFIER)
                
                # Handle optional type annotation
                type_tag = self.handleAnnotations(var_name)
                if self.checkToken(TokenType.EQ, TokenType.COMMA):
                    self.nextToken()
                else:
                    report("Missing '=' or ',' in variable declaration. use '=' for single declaration or ',' for multiple declaration.", type_="Syntax",line=self.lineNumber)
                    self.panic()
                    
                node = self.handleVarDecl(var_name, type_tag)
    
            elif self.checkToken(TokenType.IDENTIFIER):
                name = self.currentToken.value
                self.match(TokenType.IDENTIFIER)

                if self.checkToken(TokenType.INCREMENT):
                    node = self.handleIncr(name)

                elif self.checkToken(TokenType.DECREMENT):
                    node = self.handleDecr(name)

                elif self.checkToken(TokenType.DOT):
                    node = self.handleMethCall(name)

                elif self.checkToken(TokenType.LPAREN):
                    node = self.handleFuncCalls(name)

                elif self.checkToken(TokenType.EQ, TokenType.COMMA, TokenType.PLUS_EQUAL, TokenType.MINUS_EQUAL):
                    node = self.handleVarAssign(name)


                else:
                    if self.identSuggestions() is None:
                        report(f"Invalid token after the identifier '{name}'. Allowed operations with Identifiers: [Assignment, Increment, Decrement, MethodCalls, FunctionCalls] ",type_="Syntax",line=self.lineNumber)
                    self.panic()
                
            elif self.checkToken(TokenType.NEWLINE):
                self.nl()
            
            elif self.checkToken(TokenType.LBRACE):
                node = self.block()
            
            # catch-all
            else:
                if self.currentToken is not None and self.reportUnknownTok() is None:
                    report(f"Invalid statement at: '{self.currentToken.value}' ({self.currentToken.type.name})", line=self.lineNumber, type_="Syntax")
                self.panic()   
        
        except ExitSignal:
            raise ExitSignal()        
        except Exception as e:
            report(f"{e}")
            self.panic()
        
        self.nl()  
        return node or None

    # ------------ Statement Helpers ----------------- #

    def handleIncr(self, var_name):
        self.match(TokenType.INCREMENT)
        return VariableUpdated(
            var_name,
            BinaryOp(VariableReference(var_name, line=self.lineNumber), '+', Integer(1)),
            self.lineNumber
        )

    def handleDecr(self, var_name):
        self.match(TokenType.DECREMENT)
        return VariableUpdated(
            var_name,
            BinaryOp(VariableReference(var_name, line=self.lineNumber), '-', Integer(1)),
            self.lineNumber
        )

    def handleAnnotations(self, var_name):
        type_tag = None
        if self.checkToken(TokenType.COLON):
            self.nextToken()
            type_annotation = self.currentToken.value
            self.nextToken()
            type_tag = self.validateTyStr(type_annotation)
            if type_tag == 'invalid':
                report(f"Invalid type annotation received: '{type_annotation}' ", type_="Type Annotation", line=self.lineNumber)
                type_tag = None
        return type_tag

    def handleVarDecl(self, var_name, type_tag):
        if self.checkToken(TokenType.IDENTIFIER) and self.checkPeek(TokenType.COMMA, TokenType.COLON):
            variables = [var_name]
            nodes = []
            # Multiple variable declaration. set x,y,z = 10
            while self.checkToken(TokenType.IDENTIFIER):
                var_name = self.currentToken.value
                self.match(TokenType.IDENTIFIER, errorMsg=f"Expected variable name, got: '{self.currentToken.value}'")
                if self.checkToken(TokenType.COLON):
                    cur_ty_tag = self.handleAnnotations(var_name)
                    if cur_ty_tag is not None and type_tag is None:
                        type_tag = cur_ty_tag
                    if cur_ty_tag != type_tag:
                        report(
                            f"Expected type '{type_tag}', received: '{cur_ty_tag}' for variable '{var_name}'. "
                            "All type tags must be the same in multiple variable declarations (tip: just set the first one)",
                            type_="Syntax",
                            line=self.lineNumber
                        )
                variables.append(var_name)
                if self.checkToken(TokenType.EQ):
                    self.nextToken()
                    break
                if self.checkToken(TokenType.NEWLINE):
                    report(
                        f"Expected an expression for the multiple variable declaration on line {self.lineNumber}. "
                        "Please ensure it is in format:\n\t 'set x,y,z = 10'",
                        type_="Syntax",
                        line=self.lineNumber
                    )
                    self.nextToken()
                    return
                self.nextToken()

            var_expr = self.expression()

            for var in variables:
                var_node = VariableDeclaration(var, var_expr, annotation=type_tag, line=self.lineNumber)
                nodes.append(var_node)
                
            return nodes

        else:
            var_expr = self.expression()
            node = VariableDeclaration(var_name, var_expr, annotation=type_tag, line=self.lineNumber)
            return node

    def handleVarAssign(self, var_name):
        # Handle += and -=
        if self.checkToken(TokenType.PLUS_EQUAL, TokenType.MINUS_EQUAL):
            assignment_operator = self.currentToken.value
            self.nextToken()
            expr = self.expression()
            
            operator = assignment_operator[0]
            
            var_ref = VariableReference(var_name)
            bin_op_expr = BinaryOp(var_ref, operator, expr)
            var_update_node = VariableUpdated(var_name, bin_op_expr, line=self.lineNumber)
            return var_update_node

        self.match(TokenType.EQ, TokenType.COMMA, errorMsg=f"Expected '=' for single assignment or ',' for multiple assignment. instead received: {self.currentToken.value}")
        
        # Handle multiple assignments: x,y = 10
        if self.checkToken(TokenType.IDENTIFIER) and self.checkPeek(TokenType.COMMA, TokenType.EQ):
            vars = [var_name]
            while self.checkToken(TokenType.IDENTIFIER):
                var_name = self.currentToken.value
                self.nextToken()
                vars.append(var_name)
                if self.checkToken(TokenType.EQ):
                    self.nextToken()
                    break
                self.nextToken()  # skip comma
            
            expr = self.expression()
            if expr is None:
                report(
                    f"Expected an expression in variable assignment for variable: '{vars[-1]}'. "
                    f"Got: {repr(self.currentToken.value)} instead",
                    type_="Syntax",
                    line=self.lineNumber
                )
            
            nodes = []
            for var in vars:
                var_update_node = VariableUpdated(var, expr, line=self.lineNumber)
                nodes.append(var_update_node)
            
            return nodes
        else:
            expr = self.expression()
            var_update_node = VariableUpdated(var_name, expr, line=self.lineNumber)
            return var_update_node

    def handleFuncCalls(self, func_name):
        """Parses function calls"""
        self.match(TokenType.LPAREN)
        
        args = []
        while not self.checkToken(TokenType.RPAREN, TokenType.EOF, TokenType.NEWLINE):
            arg_value = self.expression()
            if arg_value is not None:
                argument_node = Argument(arg_value)
                args.append(argument_node)
            if self.checkToken(TokenType.COMMA):
                self.match(TokenType.COMMA)
        self.match(TokenType.RPAREN, errorMsg=f"Could not find enclosing bracket ')' for the function call: {func_name}(...")
        
        node = FunctionCall(func_name, args, line=self.lineNumber)
        
        if self.checkToken(TokenType.DOT):
            return self.handleMethCall(node)
        
        return node
  
    def handleMethCall(self, receiver):
        """Parses member method chains"""
        while self.checkToken(TokenType.DOT):
            self.nextToken()
            method_name = self.currentToken.value
            self.match(TokenType.IDENTIFIER)
            self.match(TokenType.LPAREN, errorMsg=f"Missing opening '(' parenthesis after method call: {method_name}")
            arguments = []
            while not self.checkToken(TokenType.RPAREN, TokenType.EOF, TokenType.NEWLINE):
                arg_value = self.expression()
                if arg_value is not None:
                    argument_node = Argument(arg_value)
                    arguments.append(argument_node)
                if self.checkToken(TokenType.COMMA):
                    self.match(TokenType.COMMA)
            self.match(TokenType.RPAREN, errorMsg=f"Could not find enclosing bracket ')' for the method call: {method_name}(...")
            receiver = MethodCall(receiver, method_name, arguments, self.lineNumber)
        return receiver

    def block(self, appendNode=None ):
        self.match(TokenType.LBRACE)
        
        # most of the time, a block will be followed by a newline
        if self.checkToken(TokenType.NEWLINE):
            self.nl()
            
        statements = []
        while not self.checkToken(TokenType.RBRACE) and not self.checkToken(TokenType.EOF):
            statement = self.statement()
        
            if statement is not None:     
                if isinstance(statement, list):
                    statements.extend(statement)
                else:
                    statements.append(statement)
        
        currentTokenErrFormat = "End of File" if self.checkToken(TokenType.EOF) else self.currentToken.value
        self.match(TokenType.RBRACE,errorMsg="Blocks must be closed by a '}' right brace,"+f"got: '{currentTokenErrFormat}'")
        
        # For loops are desugared to a while loop. we append increment node to the block
        if appendNode:
            statements.append(appendNode)
        return Block(statements)

    # ---------------- Expression Parsing ----------------- #
    
    # Calling self.expression() is more readable than self.logical()
    def expression(self):
        return self.logical()  
    
    # for  && and || operators
    def logical(self):
        node = self.equality()  # Logical comes after equality in precedence
        while self.checkToken(TokenType.AND) or self.checkToken(TokenType.OR):
            logical_operator = self.currentToken.value
            self.nextToken()
            right = self.equality()
            node = LogicalOp(node, logical_operator, right, self.lineNumber)
        return node
    
    # for == and != operators
    def equality(self):
        node = self.comparison()  # Equality comes after comparison in precedence
        while self.checkToken(TokenType.EQEQ) or self.checkToken(TokenType.NOTEQ):
            operator = self.currentToken.value
            self.nextToken()
            right = self.comparison()
            node = Comparison(node, operator, right, self.lineNumber)
        return node

    # for <, <=, >, >= operators
    def comparison(self):
        node = self.additive()  # Comparison comes after additive in precedence
        while self.isComparisonOperator():
            operator = self.currentToken.value
            self.nextToken()
            right = self.additive()
            node = Comparison(node, operator, right, self.lineNumber)
        return node
    
    # for + and - operators
    def additive(self):
        node = self.term()  # Additive comes after term in precedence
        while self.checkToken(TokenType.PLUS) or self.checkToken(TokenType.MINUS):
            operator = self.currentToken.value
            self.nextToken()
            right = self.additive()
            binOp = BinaryOp(node, operator, right, line=self.lineNumber)
            return binOp
        return node

    # for *, /, % operators 
    def term(self):
        node = self.factor()  # Term comes after factor in precedence
        while self.checkToken(TokenType.ASTERISK, TokenType.SLASH, TokenType.MODUlO):
            operator = self.currentToken.value
            self.nextToken()
            right = self.factor()
            node = BinaryOp(node, operator, right, self.lineNumber)
        return node
    
    # for ^ operator (exponentiation)
    def factor(self):
        node = self.unary()  # Factor comes after unary in precedence
        while self.checkToken(TokenType.POW): 
            operator = self.currentToken.value
            self.nextToken()
            if self.checkToken(TokenType.NEWLINE):
                right = Double(2)
            else: 
                right = self.unary()
            node = BinaryOp(node, operator, right, self.lineNumber)
        return node

    # for +5, -5, and ! operators
    def unary(self):
        operator = None
        if self.checkToken(TokenType.PLUS) or self.checkToken(TokenType.MINUS) or self.checkToken(TokenType.NOT):
            operator = self.currentToken.value
            self.nextToken()
        
        node = self.primary()
        if operator:
            node = UnaryOp(operator, node, self.lineNumber)
            
        return node

    # for literals and nested expressions
    def primary(self):
        node = None
        
        if self.checkToken(TokenType.INTEGER):
            node = Integer(value=int(self.currentToken.value), line=self.lineNumber)
            self.nextToken()
        
        elif self.checkToken(TokenType.DOUBLE):
            try:
                node = Double(float(self.currentToken.value), self.lineNumber)
                self.nextToken()
            except ValueError:
                report(f"Invalid float value: {self.currentToken.value}", line=self.lineNumber, type_="Syntax")
        
        elif self.checkToken(TokenType.BOOLEAN):
            try:
                value = "true" if self.currentToken.value == "true" else "false"
                node = Boolean(value, self.lineNumber)
                self.nextToken()
            except ValueError:
                report(f"Invalid boolean value: {self.currentToken.value}", line=self.lineNumber, type_="Syntax")
        
        elif self.checkToken(TokenType.STRING):
            node = String(self.currentToken.value, line=self.lineNumber)
            self.nextToken()
            
        elif self.checkToken(TokenType.NULL):
            node = Null(self.lineNumber)
            self.nextToken()
        
        elif self.checkToken(TokenType.IDENTIFIER):
            var_name = self.currentToken.value
            self.match(TokenType.IDENTIFIER)
            
            if self.checkToken(TokenType.LPAREN):
                node = self.handleFuncCalls(var_name)
            elif self.checkToken(TokenType.DOT):
                node = self.handleMethCall(receiver=VariableReference(var_name, line=self.lineNumber))
            else:
                if self.checkToken(TokenType.INCREMENT):
                    self.nextToken()
                    node = VariableUpdated(var_name, BinaryOp(VariableReference(var_name, line=self.lineNumber), '+', Integer(1)), self.lineNumber)
                elif self.checkToken(TokenType.DECREMENT):
                    self.nextToken()
                    node = VariableUpdated(var_name, BinaryOp(VariableReference(var_name, line=self.lineNumber), '-', Integer(1)), self.lineNumber)
                else:
                    node = VariableReference(var_name, line=self.lineNumber)
        
        elif self.checkToken(TokenType.LPAREN):
            self.nextToken()
            node = self.expression()
            self.match(TokenType.RPAREN,errorMsg=f"Missing closing parenthesis for expression on line {self.lineNumber}")
        
        # Catch-all
        else:
            report(f"Unexpected token in expression: {repr(self.currentToken.value)}", line=self.lineNumber, type_="Syntax")
        
        return node 

