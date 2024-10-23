class ASTNode:
    def __init__(self):
            self.parent = None
            self.parent_attr = None 
            self.parent_index = None  
            
    def replace_self(self, new_node):
        """ Replaces "self"(the callee) with the new_node argument. If new_node is None will delete "self" instead """
        if not self.parent:
            raise ValueError("Cannot replace node without a parent")
        
        if self.parent_attr:
            parent_attr = getattr(self.parent, self.parent_attr)

            if isinstance(parent_attr, list) and self.parent_index is not None:
                # Replace or delete in list
                if new_node is None:
                    # Remove the current node from the list
                    del parent_attr[self.parent_index]
                else:
                    # Replace with the new node in the list
                    parent_attr[self.parent_index] = new_node
                    new_node.parent = self.parent
                    new_node.parent_attr = self.parent_attr
                    new_node.parent_index = self.parent_index

                # Clear current node's references
                self.parent = None
                self.parent_attr = None
                self.parent_index = None

            else:
                # Replace or delete an attribute
                if new_node is None:
                    # Set the attribute to None, effectively deleting it
                    setattr(self.parent, self.parent_attr, None)
                else:
                    # Replace with the new node
                    setattr(self.parent, self.parent_attr, new_node)
                    new_node.parent = self.parent
                    new_node.parent_attr = self.parent_attr

                # Clear current node's references
                self.parent = None
                self.parent_attr = None
                self.parent_index = None

        else:
            raise ValueError("Parent context not set for node replacement")

    def accept(self, visitor):
        raise NotImplementedError("Subclasses should implement this!")

    def print_content(self, indent=0):
        raise NotImplementedError("Subclasses should implement this!")

class Program(ASTNode):
    def __init__(self, statements):
        super().__init__()
        self.statements = statements
        for index, stmt in enumerate(self.statements):
            if stmt is not None:
                stmt.parent = self
                stmt.parent_attr = 'statements'
                stmt.parent_index = index

        # This dict stores refs to nodes we might want to transform later.
        self.stats = {
            'if': [],
            'while': [],
            'funcDecl': [],
            'funcCall': [],
            'varDecl': [],
            'varRef': [],
            'varUpdate': [],
            'comparison': [],
            'binOp': [],
            'logOp': [],
            'passNo': 0     
        }
        
    def __eq__(self, other):
        return isinstance(other, Program) and self.statements == other.statements
    
    def __str__(self):
        return f"Program({self.statements})"
    
    def accept(self, visitor):
        return visitor.visit_program(self)
    
    def addRef(self, node_type, val):
        if self.stats['passNo'] >= 1:
            return
        if node_type == 'passNo':
            self.stats[node_type] = val
        elif node_type in self.stats:
            self.stats[node_type].append(val)
        else:
            self.stats[node_type] = [val]
    
    def print_content(self, indent=0, printStats=False):
        
        if printStats:
            print("Recorded Stats: ")
            self.pretty_print_stats() 
        for stmt in self.statements:
            if stmt is not None:
                stmt.print_content(indent + 2)
            else:
                print(" " * (indent + 2) + "null")

    def pretty_print_stats(self):
        print("---------------------")
        for node_type, nodes in self.stats.items():
            print(f"{node_type.capitalize()}: {len(nodes)} nodes")
            if nodes:
                print("    References:")
                for i, node in enumerate(nodes):
                    print(f"    {i + 1}. {node}")  
            else:
                print("    No references.")
            print()  
        print("---------------------")
        
class Block(ASTNode):
    def __init__(self, statements):
            super().__init__()
            self.statements = statements
            for index, stmt in enumerate(self.statements):
                if stmt is not None:
                    stmt.parent = self
                    stmt.parent_attr = 'statements'
                    stmt.parent_index = index
              
    def __eq__(self, other):
        return isinstance(other, Block) and self.statements == other.statements

    def __str__(self):
        return f"Block({self.statements})"

    def accept(self, visitor):
        return visitor.visit_block(self)

    def print_content(self, indent=0):
        print(" " * indent + "Block")
        for stmt in self.statements:
            if stmt is not None:
                stmt.print_content(indent + 2)
            else:
                print(" " * (indent+2) + "null")
        
class VariableDeclaration(ASTNode):
    def __init__(self, name, value, line=None, annotation=None):
        super().__init__()
        self.name = name
        self.value = value
        self.annotation = annotation
        self.line = line
        if self.value is not None:
            self.value.parent = self
            self.value.parent_attr = 'value'
    
    def evaluateType(self):
        if self.value is not None:
            return self.value.evaluateType()
        return "invalid"
    
    def __eq__(self, other):
        return (isinstance(other, VariableDeclaration) and
                self.name == other.name and
                self.value == other.value)
        
    def __str__(self):
        return f"set '{str(self.name)}' '=' '{str(self.value)}'"

    def __repr__(self):
        return f"VariableDeclaration('{self.name}')"
        
    def accept(self, visitor):
            return visitor.visit_variable(self)

    def print_content(self, indent=0):
        print(" " * indent + f"VariableDeclaration: {self.name}")
        if self.annotation is not None:
            print(" " * (indent + 2) + f"Type Annotation: {self.annotation}")
        if self.value is not None:
            self.value.print_content(indent + 2)
        else:
            print(" " * (indent + 2) + "Value: None")

class VariableReference(ASTNode):
    def __init__(self, name, line = None):
        super().__init__()
        self.name = name
        self.line = line
        
        # set in analyzer
        self.value = None
        self.type = None
        self.scope = None
        
    def evaluateType(self):
        if self.type is not None:
            return self.type
        return 'invalid'
        
    def __eq__(self, other):
        return (isinstance(other, VariableReference) and self.name == other.name)
        
    def __str__(self):
        return f"{str(self.name)}"
        
    def __repr__(self):
        return  f"VariableReference({self.name})"
    
    def accept(self, visitor):
        return visitor.visit_variable(self)

    def print_content(self, indent=0):
        _ = f":'{self.type}'" if self.type is not None else ""
        print(" " * indent + f"VariableReference: '{self.name}':{ _ } ")

class VariableUpdated(ASTNode):
    def __init__(self, name, value, line=None):
        super().__init__()
        self.name = name
        self.value = value
        self.line = line
        if self.value is not None:
            self.value.parent = self
            self.value.parent_attr = 'value'
    
    def evaluateType(self):
        if self.value is not None:
            return self.value.evaluateType()
        return "invalid"
    
    def __eq__(self, other):
        return (isinstance(other, VariableUpdated) and
                self.name == other.name and
                self.value == other.value)
        
    def __str__(self):
        return f"{self.name} = {str(self.value)}"
    
    def __repr__(self):
        return f"VariableUpdated({str(self.name)})"
        
    def accept(self, visitor):
        return visitor.visit_variable(self)
    
    def print_content(self, indent=0):
        print(" " * indent + f"VariableUpdated: {self.name} ")
        if self.value is not None:
            self.value.print_content(indent + 2)
        else:
            print(" " * (indent + 2) + "Value: None")

class FunctionDeclaration(ASTNode):
    def __init__(self, name, return_type, parameters, block, line=None):
        super().__init__()
        self.name = name
        self.return_type = return_type
        self.parameters = parameters
        self.block = block
        self.arity = len(parameters)
        self.line = line
        # Set parent references
        for index, param in enumerate(self.parameters):
            param.parent = self
            param.parent_attr = 'parameters'
            param.parent_index = index
        if self.block is not None:
            self.block.parent = self
            self.block.parent_attr = 'block'

        
    def __eq__(self, other):
        return (isinstance(other, FunctionDeclaration) and
                self.name == other.name and
                self.parameters == other.parameters and
                self.block == other.block)
    
    def __str__(self):
        params_str = ', '.join([str(param) for param in self.parameters])
        return f"function {str(self.name)}([{params_str}]) {{...}}"
    
    def __repr__(self):
        return f"FunctionDeclaration({str(self.name)})"
    
    def accept(self, visitor):
        return visitor.visit_function_declaration(self)
    
    def print_content(self, indent=0):
        print(" " * indent + f"FunctionDeclaration: {self.name} (return_type: {self.return_type})")
        print(" " * (indent + 2) + f"Parameters: ({self.parameters})")
        print(" " * (indent + 2) + f"Parent: ({self.parent})")
        self.block.print_content(indent + 2)

class Return(ASTNode):
    def __init__(self, value, line = None):
        super().__init__()
        self.value = value
        self.line = line
        # Set parent reference for value
        if self.value is not None:
            self.value.parent = self
            self.value.parent_attr = 'value'
     
    def evaluateType(self):
        if self.value is not None:
            return self.value.evaluateType()
        return 'invalid'
    
    def __str__(self):
        return f"{str(self.value)}"
    
    def __repr__(self):
        return f"Return({repr(self.value)})"

    def __eq__(self, other):
        return isinstance(other, Return) and self.value == other.value
    
    def accept(self, visitor):
        return visitor.visit_return(self)
    
    def print_content(self, indent=0):
        print(" " * indent + f"Return: {self.value}")

class Break(ASTNode):
    def __init__(self, line):
        super().__init__()
        self.line = line
    
    def __str__(self):
        return "Break"
    
    def __repr__(self):
        return "Break"

    def __eq__(self, other):
        return isinstance(other, Break)
    
    def accept(self, visitor):
        return visitor.visit_break(self)
    
    def print_content(self, indent=0):
        print(" "*indent + "Break")
    
class Parameter(ASTNode):
    def __init__(self, name, type):
        super().__init__()
        self.name = name
        self.type = type
    
    def evaluateType(self):
        return self.type
    
    def __str__(self):
        return f"{self.name}"
    
    def __repr__(self):
        return f"Parameter({self.name})"

    def __eq__(self, other):
        return isinstance(other, Parameter) and self.type == other.type
    
    def accept(self, visitor):
        return visitor.visit_parameter(self)
    
    def print_content(self, indent=0):
        print(" " * indent + f"Parameter: {self.name} (type: {self.type})")

class FunctionCall(ASTNode):
    def __init__(self, name, args, line=None):
        super().__init__()
        self.name = name
        self.args = args
        self.arity = len(args)
        self.line = line
        self.type = None     # set in analyzer
        self.transformed = None
        # Set parent references for arguments
        for index, arg in enumerate(self.args):
            arg.parent = self
            arg.parent_attr = 'args'
            arg.parent_index = index
    
    def evaluateType(self):
        if self.type is not None:
            return self.type
        return 'invalid'
    
    def accept(self, visitor):
        return visitor.visit_function_call(self)
    
    def replace_with(self, new_node):
        attrs = ['value', 'receiver', 'arguments', 'left','right'] 

        def recursive_replace(node, parent, attr_name):
            """ Recursively search for and replace `self` within specified attributes. """
            if isinstance(node, (list, tuple)):
                for index, item in enumerate(node):
                    if item == self:
                        if isinstance(node, list):
                            node[index] = new_node
                        else:
                            node = node[:index] + (new_node,) + node[index + 1:]
                            setattr(parent, attr_name, node)
                        return True
                    for attr in attrs:
                        if hasattr(item, attr):
                            if recursive_replace(getattr(item, attr), item, attr):
                                return True
            elif isinstance(node, dict):
                for key, item in node.items():
                    if item == self:
                        node[key] = new_node
                        return True
                    for attr in attrs:
                        if hasattr(item, attr):
                            if recursive_replace(getattr(item, attr), item, attr):
                                return True
            elif node == self:
                setattr(parent, attr_name, new_node)
                return True
            else:
                for attr in attrs:
                    if hasattr(node, attr):
                        if recursive_replace(getattr(node, attr), node, attr):
                            return True
            return False

        if self.parent:
            # Look through all attributes of the parent object
            for attr, value in vars(self.parent).items():
                if recursive_replace(value, self.parent, attr):
                    new_node.parent = self.parent
                    self.transformed = True
                    del self
                    return

            new_node.parent = self.parent
    
    def __eq__(self, other):
        return (isinstance(other, FunctionCall) and
                self.name == other.name and
                self.args == other.args and
                self.parent == other.parent)
    
    def __str__(self):
        _ = ",".join(str(arg) for arg in self.args) if self.args else ""
        return f"{str(self.name)}({ _ })"
        
    def __repr__(self):
        return f"FunctionCall({str(self.name)})"
    
    def print_content(self, indent=0):
        print(" " * indent + f"FunctionCall: {self.name}")
        if self.parent is not None:
            print(" " * (indent + 2) + f"parent : {self.parent}")
        if len(self.args) > 0:
            for arg in self.args:
                arg.print_content(indent + 2)
        else:
            print(" " * (indent + 2) + "Arguments: None")

class Argument(ASTNode):
    def __init__(self, value, name = None):
        super().__init__()
        self.name = name
        self.value = value
        self.cached_type = None
        # Set parent reference for value
        if self.value is not None and isinstance(self.value, ASTNode):
            self.value.parent = self
            self.value.parent_attr = "value"
    
    def evaluateType(self):
        if self.cached_type is not None:
            return self.cached_type
        else:
            return self.value.evaluateType()
    
    def __str__(self):
        if isinstance(self.value, list):
            list_str = ', '.join(str(item) for item in self.value)
            return f"[{list_str}]"
        else:
            return f"{str(self.value)}"
    
    def __repr__(self):
        if isinstance(self.value, list):
            list_str = ', '.join(repr(item) for item in self.value)
            return f"Argument([{list_str}])"
        else:
            return f"Argument({repr(self.value)})"

    def __eq__(self, other):
        return isinstance(other, Argument) and self.type == other.type
    
    def accept(self, visitor):
        return visitor.visit_argument(self)
    
    def print_content(self, indent=0):
        print(" " * indent + f"Argument: {repr(self.value)}")
        if self.parent is not None:
            print(" " * (indent+2) + f"parent: {repr(self.parent)}")

class MethodCall(ASTNode):
    def __init__(self, receiver, name, args, line=None):
        super().__init__()
        self.receiver = receiver
        self.name = name
        self.args = args
        self.receiverTy = None
        self.line = line
        # Set parent references
        if self.receiver is not None:
            self.receiver.parent = self
        for arg in self.args:
            arg.parent = self
    
    def evaluateType(self):
        if self.return_type is not None:
            return self.return_type
        return 'invalid'
    
    def __eq__(self, other):
        return (isinstance(other, MethodCall) and
                self.receiver == other.receiver and
                self.name == other.name and
                self.args == other.args)
        
    def __str__(self):
        _ = ",".join(str(arg) for arg in self.args) if self.args else ""
        return f"{str(self.receiver)}.{str(self.name)}({ _ })"

    def __repr__(self):
        return f"MethodCall({str(self.receiver)}.{str(self.name)}(...))"
        
    def accept(self, visitor):
        return visitor.visit_method_call(self)
    
    def print_content(self, indent=0):
        print(" " * indent + f"MethodCall: {self.name}()")
        if isinstance(self.receiver, MethodCall):
            print(" " * (indent + 2) + "Receiver:")
            self.receiver.print_content(indent + 4)
        else:
            print(" " * (indent + 2) + f"Receiver: {self.receiver}")

        if self.args:
            print(" " * (indent + 2) + "Arguments:")
            for arg in self.args:
                arg.print_content(indent + 4)
        else:
            print(" " * (indent + 2) + "Arguments: None")
            
class If(ASTNode):
    def __init__(self, comparison, block, line=None, elifNodes=[], elseBlock=None):
        super().__init__()
        self.comparison = comparison
        self.block = block
        self.elifNodes = elifNodes if elifNodes else []  # an array of tuples in format: (comparison, block)
        self.elseBlock = elseBlock
        self.line = line
        
        # Set parent reference and context for the comparison
        if self.comparison is not None:
            self.comparison.parent = self
            self.comparison.parent_attr = 'comparison'

        # Set parent reference and context for the main block
        if self.block is not None:
            self.block.parent = self
            self.block.parent_attr = 'block'

        # Set parent reference and context for elif nodes
        for index, (elif_comparison, elif_block) in enumerate(self.elifNodes):
            if elif_comparison is not None:
                elif_comparison.parent = self
                elif_comparison.parent_attr = 'elifNodes'
                elif_comparison.parent_index = index

            if elif_block is not None:
                elif_block.parent = self
                elif_block.parent_attr = 'elifNodes'
                elif_block.parent_index = index

        # Set parent reference and context for the else block
        if self.elseBlock is not None:
            self.elseBlock.parent = self
            self.elseBlock.parent_attr = 'elseBlock'

    def __eq__(self, other):
        return (isinstance(other, If) and
                self.comparison == other.comparison and
                self.block == other.block and
                self.elifNodes == other.elifNodes and
                self.elseBlock == other.elseBlock)
    
    def __str__(self):
        return f"{str(self.comparison)}"
    
    def __repr__(self):
        return f"If({repr(self.comparison)})"
    
    def accept(self, visitor):
        return visitor.visit_if(self)
    
    def print_content(self, indent=0):
            print(" " * indent + "If")
            
            if self.comparison:
                self.comparison.print_content(indent + 2)
            else:
                print(" " * (indent + 2) + "None")
            
            if self.block:
                self.block.print_content(indent + 2)
            else:
                print(" " * (indent + 2) + "None")
            
            if self.elifNodes:
                for elif_comparison, elif_block in self.elifNodes:
                    print(" " * indent + "Elif")
                    if elif_comparison:
                        elif_comparison.print_content(indent + 2)
                    else:
                        print(" " * (indent + 2) + "None")
                    if elif_block:
                        elif_block.print_content(indent + 2)
                    else:
                        print(" " * (indent + 2) + "None")
            
            if self.elseBlock is not None:
                print(" " * indent + "Else")
                self.elseBlock.print_content(indent + 2)      

class While(ASTNode):
    def __init__(self, comparison, block, line=None):
        super().__init__()
        self.comparison = comparison
        self.block = block
        self.line = line
        if self.comparison is not None:
            self.comparison.parent = self
            self.comparison.parent_attr = 'comparison'
        if self.block is not None:
            self.block.parent = self
            self.block.parent_attr = 'block'
        
    def __eq__(self, other):
        return isinstance(other, While) and self.comparison == other.comparison and self.block == other.block

    def __str__(self):
        return f"{str(self.comparison)}"
        
    def __repr__(self):
        return f"While({repr(self.comparison)})"
        
    def accept(self, visitor):
        return visitor.visit_while(self)
    
    def print_content(self, indent=0):
        print(" " * indent + "While")
        self.comparison.print_content(indent + 2)
        self.block.print_content(indent + 2)
       
class StringCat(ASTNode):
    """ Holds string concatenations. Will be transformed from BinaryOps. The strings array holds all the values to be concatenated """
    def __init__(self, strings, parent, line=None):
        super().__init__()
        self.strings = strings
        self.line = line
        self.evaluated = None 
        self.visited = False
        # Set parent references for strings
        for idx, s in enumerate(self.strings):
            if isinstance(s, String):
                s.parent = self
                s.parent_attr = 'strings'
                s.parent_index = idx

    def evaluateType(self):
        return "string"

    def accept(self, visitor):
        return visitor.visit_string_cat(self)
    
    def __str__(self):
        _ = f"{str(self.evaluated)}" if self.evaluated is not None else f"{str(self.strings)}"
        return f"{ _ }"

    def __repr__(self):
        _ = "True" if self.evaluated is not None else "False"
        return f"StringCat(eval: { _ })"
    
    def __eq__(self, other):
        return (isinstance(other, StringCat) and
                self.parent == other.parent and
                self.strings == other.strings and
                self.evaluated == other.evaluated)

    def print_content(self, indent=0):
        _ = "True" if self.evaluated is not None else "False"
        print(" " * indent + f"StringCat (evaluated: {_})")
        if self.evaluated is not None:
            print(" " * (indent+2) + f"{self.evaluated}")
        else:
            for value in self.strings:
                if isinstance(value, ASTNode):
                    value.print_content(indent + 2)
                else:
                    print(" " *(indent +2) +f"{str(value)}")
    
# ------------------------- Expressions ------------------------- #
class Expression(ASTNode):
    def __init__(self, left, operator, right, line=None):
        super().__init__()
        self.left = left
        self.operator = operator
        self.right = right
        self.line = line
        # Set parent references
        if self.left is not None:
            self.left.parent = self
            self.left.parent_attr = 'left'
        if self.right is not None:
            self.right.parent = self
            self.right.parent_attr = 'right'
    
    def __eq__(self, other):
        raise NotImplementedError("Subclasses should implement this!")

    def accept(self, visitor):
        raise NotImplementedError("Subclasses should implement this!")
    
    def __str__(self):
        raise NotImplementedError("Subclasses should implement this!")
    
    def print_content(self, indent=0):
        print(" " * indent + "Expression")
        self.left.print_content(indent + 2)
        print(" " * (indent + 2) + f"Operator: {self.operator}")
        self.right.print_content(indent + 2)

# For + - * /
class BinaryOp(Expression):
    def __init__(self, left, operator, right, line=None):
        super().__init__(left, operator, right, line)
        self.cached_type = None
        self.transformed = None     # flag to know if binaryOp has been transformed

    def evaluateType(self):
        if self.cached_type is not None:
            return self.cached_type
        
        left_type = self.left.evaluateType()
        right_type = self.right.evaluateType()
        numeric_types = ['integer', 'double']
        
        if self.operator in ['+', '-', '*', '/', '%','^']:
            if left_type in numeric_types and right_type in numeric_types:
                # If one is double, the result is double
                if left_type == 'double' or right_type == 'double':
                    self.cached_type = 'double'
                else:
                    self.cached_type = 'integer'
            elif (self.operator == '+') and (left_type == 'string' or right_type == 'string'):
                self.cached_type = 'string'

        return self.cached_type or "invalid"
    
    def accept(self, visitor):
        return visitor.visit_binary_op(self)

    def __str__(self):
        return f"{str(self.left)} '{self.operator}' {str(self.right)}"
 
    def __repr__(self):
        return f"BinaryOp({repr(self.left)} '{self.operator}' {repr(self.right)})"

    def __eq__(self, other):
        return (isinstance(other, BinaryOp) and
                self.left == other.left and
                self.operator == other.operator and
                self.right == other.right)

    def print_content(self, indent=0):
        print(" " * indent + f"BinaryOp (Operator {self.operator})")
        self.left.print_content(indent + 2)
        self.right.print_content(indent + 2)
   
# for -5 / +5 and !
class UnaryOp(Expression):
    def __init__(self, operator, left, line=None):
        super().__init__(left, operator, None, line)
        self._cached_type = None
        # Set parent reference
        if self.left is not None:
            self.left.parent = self
            self.left.parent_attr = 'left'

    def evaluateType(self):
        if self._cached_type is not None:
            return self._cached_type
        
        left_type = self.left.evaluateType()
        if self.operator == '!':
            if left_type != 'boolean':
                return "invalid"
            self._cached_type = 'boolean'
        elif self.operator == '-' or self.operator == '+':
            if left_type != 'integer' and left_type != 'double':
                return "invalid"
            self._cached_type = left_type
            
        return self._cached_type or "invalid"
    
    def accept(self, visitor):
        return visitor.visit_unary_op(self)
    
    def __str__(self):
        return f"'{self.operator}{self.left}'"

    def __repr__(self):
        return f"UnaryOp({self.operator}{repr(self.left)})"

    def __eq__(self, other):
        return (isinstance(other, UnaryOp) and
                self.operator == other.operator and
                self.left == other.left)

    def print_content(self, indent=0):
        print(" " * indent + f"UnaryOp (Operator: {self.operator})")
        self.left.print_content(indent + 2)

# for < > <= >= == !=
class Comparison(Expression):
    def __init__(self, left, operator, right, line=None):
        super().__init__(left, operator, right, line)
        self._cached_type = None
    
    def evaluateType(self):
        if self._cached_type is not None:
            return self._cached_type 
        
        left_type = self.left.evaluateType()
        right_type = self.right.evaluateType()
        if left_type not in ['integer', 'double','string','boolean'] or right_type not in ['integer', 'double','string','boolean']:
            return "invalid"
        self._cached_type = 'boolean'
        return self._cached_type
    
    def accept(self, visitor):
        return visitor.visit_comparison(self)
    
    def __str__(self):
        return f"{str(self.left)} '{self.operator}' {str(self.right)}"
    
    def __repr__(self):
        return f"Comparison({repr(self.left)} '{self.operator}' {repr(self.right)})"
    
    def __eq__(self, other):
        return (isinstance(other, Comparison) and
                self.left == other.left and
                self.operator == other.operator and
                self.right == other.right)
    
    def print_content(self, indent=0):
        print(" " * indent + f"Comparison (Operator: {self.operator})")
        self.left.print_content(indent + 2)
        self.right.print_content(indent + 2)

# for && ||
class LogicalOp(Expression):
    def __init__(self, left, operator, right, line= None):
        super().__init__(left, operator, right, line)
        self._cached_type = None

    def evaluateType(self):
        if self._cached_type is not None:
            return self._cached_type 
        
        left_type = self.left.evaluateType()
        right_type = self.right.evaluateType()
        if left_type != 'boolean' or right_type != 'boolean':
            return "invalid"
        
        self._cached_type = 'boolean'
        return self._cached_type
    
    def accept(self, visitor):
        return visitor.visit_logical_op(self)
    
    def __str__(self):
        return f"'{str(self.left)}' '{self.operator}' '{str(self.right)}'"
    
    def __repr__(self):
        return f"LogicalOp('{repr(self.left)}' '{self.operator}' '{repr(self.right)}')"

    def __eq__(self, other):
        return (isinstance(other, LogicalOp) and
                self.left == other.left and
                self.operator == other.operator and
                self.right == other.right)
    
    def print_content(self, indent=0):
        print(" " * indent + f"LogicalOp (Operator: {self.operator})")
        self.left.print_content(indent + 2)
        self.right.print_content(indent + 2)        

# ------------------------- Literals ------------------------- #

class Primary(ASTNode):
    def __init__(self, value, line=None):
        super().__init__()
        self.value = value
        self.line = line
        self.type = self.evaluateType()

    def __eq__(self, other):
        return isinstance(other, Primary) and self.value == other.value and self.line == other.line

    def __str__(self):
        return f"{self.__class__.__name__}({self.value})"
    
    def print_content(self, indent=0):
        print(" " * indent + f"{self.__class__.__name__}: {str(self.value)}")

class Integer(Primary):
    def __init__(self, value, line=None):
       super().__init__(value, line)

    def evaluateType(self):
        if isinstance(self.value, int):
            return 'integer'
        return "invalid"
    
    def __str__(self):
        return f"{str(self.value)}"
    
    def __repr__(self):
        return f"Integer({self.value})"

    def accept(self, visitor):
        return visitor.visit_integer(self)
    
class Double(Primary):
    def __init__(self, value, line=None):
        super().__init__(value, line)

    def evaluateType(self):
        if isinstance(self.value, float):
            return 'double'
        return "invalid"
      
    def __str__(self):
        return f"{str(self.value)}"
   
    def __repr__(self):
        return f"Double({self.value})"

    def accept(self, visitor):
        return visitor.visit_double(self)

class Boolean(Primary):
    def __init__(self, value, line=None):
        super().__init__(value, line)
    def evaluateType(self):
        if isinstance(self.value, str) and self.value.lower().strip() in ['true', 'false']:
            return 'boolean'
        return "invalid"
   
    def __str__(self):
        return f"{self.value}" 
   
    def __repr__(self):
        return f"Boolean({self.value})"
 
    def accept(self, visitor):
        return visitor.visit_boolean(self)

class String(Primary):
    def __init__(self, value, isTypeStr=None, line=None):
        super().__init__(value, line)
        self.isTypeStr = isTypeStr

    def evaluateType(self):
        if self.value is not None and isinstance(self.value, str):
            return 'string'
        return "invalid"

    def __str__(self):
        return f"'{self.value}'"

    def __repr__(self):
        return f'"{self.value}"'
    
    def accept(self, visitor):
        return visitor.visit_string(self)

class Null(Primary):
    def __init__(self, line=None):
        super().__init__(None, line)

    def evaluateType(self):
        return 'null'
   
    def __str__(self):
        return "Null"
   
    def __repr__(self):
        return "Null"

    def accept(self, visitor):
        return visitor.visit_null(self)

    def print_content(self, indent=0):
        print(" " * indent + "Null")