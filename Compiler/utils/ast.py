import copy
class ASTNode:
    def __init__(self):
            self.parent = None
            self.parent_attr = None 
            self.parent_index = None  
    
    def __deepcopy__(self, memo):
        """
        Generic deepcopy implementation for ASTNode.
        Subclasses can override this method if needed.
        """
        cls = self.__class__
        copied_node = cls.__new__(cls)
        memo[id(self)] = copied_node
        for attr, value in self.__dict__.items():
            if attr in ['parent', 'parent_attr', 'parent_index']:
                # These will be set by the parent during traversal
                setattr(copied_node, attr, None)
            else:
                setattr(copied_node, attr, copy.deepcopy(value, memo))
        return copied_node
    
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

        # stores refs to nodes we might transform later, reducing O(n) traversals
        self.node_registry = {
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
    
    def __deepcopy__(self, memo):
        """
        Custom deepcopy method that copies the AST and populates node_registry in the copied AST.
        """
        cls = self.__class__
        copied_program = cls.__new__(cls)
        memo[id(self)] = copied_program
        
        # Initialize node_registry in the copied program
        copied_program.node_registry = {
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
            'return': [],
            'passNo': self.node_registry['passNo']
        }
        
        # Initialize registry in memo for child nodes to access
        registry = copied_program.node_registry
        memo['registry'] = registry  
        
        # Deep copy statements
        copied_statements = []
        for index, stmt in enumerate(self.statements):
            if stmt is not None:
                copied_stmt = copy.deepcopy(stmt, memo)
                copied_stmt.parent = copied_program
                copied_stmt.parent_attr = 'statements'
                copied_stmt.parent_index = index
                copied_statements.append(copied_stmt)
                
                # Add to node_registry if applicable (handled in child deepcopy)
            else:
                copied_statements.append(None)
        
        copied_program.statements = copied_statements
        
        # Remove registry from memo to avoid side effects
        del memo['registry']
        return copied_program
    
    def get_node_type(self, node):
        """Helper method to determine the node type as a string key for node_registry."""
        type_mapping = {
            If: 'if',
            While: 'while',
            FunctionDeclaration: 'funcDecl',
            FunctionCall: 'funcCall',
            VariableDeclaration: 'varDecl',
            VariableReference: 'varRef',
            VariableUpdated: 'varUpdate',
            Comparison: 'comparison',
            BinaryOp: 'binOp',
            LogicalOp: 'logOp',
            Return: 'return'
        }
        return type_mapping.get(type(node), None)
    
    def accept(self, visitor):
        return visitor.visit_program(self)
    
    def addRef(self, node_type, val):
        if self.node_registry['passNo'] >= 1:
            return
        if node_type == 'passNo':
            self.node_registry[node_type] = val
        elif node_type in self.node_registry:
            self.node_registry[node_type].append(val)
        else:
            self.node_registry[node_type] = [val]
    
    def collect_refs(self):
        """Collect references to nodes for direct access during glitching"""
        pass_no = self.node_registry['passNo']
        self.node_registry = {
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
            'return': [],
            'passNo': pass_no
        }
        for statement in self.statements:
            self._traverse_and_collect(statement)

    def _traverse_and_collect(self, node):
        """Recursively traverse the AST and collect certain node references."""
        if isinstance(node, If):
            self.node_registry['if'].append(node)
            self._traverse_and_collect(node.block)
            for _ , block in node.elifNodes:
                if block is not None:
                    self._traverse_and_collect(block)
            if node.elseBlock is not None:
                self._traverse_and_collect(node.elseBlock)
                
        elif isinstance(node, While):
            self.node_registry['while'].append(node)
            self._traverse_and_collect(node.block)
            
        elif isinstance(node, FunctionDeclaration):
            self.node_registry['funcDecl'].append(node)
            self._traverse_and_collect(node.block)
            
        elif isinstance(node, FunctionCall):
            self.node_registry['funcCall'].append(node)
            
        elif isinstance(node, VariableDeclaration):
            self.node_registry['varDecl'].append(node)
            
        elif isinstance(node, VariableReference):
            self.node_registry['varRef'].append(node)
        
        elif isinstance(node, VariableUpdated):
            self.node_registry['varUpdate'].append(node)
        
        elif isinstance(node, Comparison):
            self.node_registry['comparison'].append(node)
        
        elif isinstance(node, BinaryOp):
            self.node_registry['binOp'].append(node)
        
        elif isinstance(node, LogicalOp):
            self.node_registry['logOp'].append(node)

        elif isinstance(node, Return):
            self.node_registry['return'].append(node)
        
        elif isinstance(node, Block):
            for statement in node.statements:
                self._traverse_and_collect(statement)
        
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

    def __deepcopy__(self, memo):
        cls = self.__class__
        copied_block = cls.__new__(cls)
        memo[id(self)] = copied_block

        # Deep copy the statements and set parent references
        copied_statements = []
        for index, stmt in enumerate(self.statements):
            if stmt is not None:
                copied_stmt = copy.deepcopy(stmt, memo)
                copied_stmt.parent = copied_block
                copied_stmt.parent_attr = 'statements'
                copied_stmt.parent_index = index
                copied_statements.append(copied_stmt)
            else:
                copied_statements.append(None)

        copied_block.statements = copied_statements

        return copied_block

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
 
    def __eq__(self, other):
        return (isinstance(other, VariableDeclaration) and
                self.name == other.name and
                self.value == other.value)
        
    def __str__(self):
        return f"set '{str(self.name)}' '=' '{str(self.value)}'"

    def __repr__(self):
        return f"VariableDeclaration('{self.name}')"
        
    def __deepcopy__(self, memo):
        cls = self.__class__
        copied_var_decl = cls.__new__(cls)
        memo[id(self)] = copied_var_decl

        # Copy attributes
        copied_var_decl.name = copy.deepcopy(self.name, memo)
        copied_var_decl.value = copy.deepcopy(self.value, memo)
        copied_var_decl.annotation = copy.deepcopy(self.annotation, memo)
        copied_var_decl.line = self.line

        # Set parent references
        if copied_var_decl.value is not None:
            copied_var_decl.value.parent = copied_var_decl
            copied_var_decl.value.parent_attr = 'value'

        # Register the copied variable declaration in the node registry
        registry = memo.get('registry', None)
        if registry is not None:
            registry['varDecl'].append(copied_var_decl)

        return copied_var_decl
    
    def evaluateType(self):
        if self.value is not None:
            return self.value.evaluateType()
        return "invalid"
    
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
        
    def __eq__(self, other):
        return (isinstance(other, VariableReference) and self.name == other.name)
        
    def __str__(self):
        return f"{str(self.name)}"
        
    def __repr__(self):
        return  f"VariableReference({self.name})"
    
    def __deepcopy__(self, memo):
        cls = self.__class__
        copied_var_ref = cls.__new__(cls)
        memo[id(self)] = copied_var_ref

        # Copy attributes
        copied_var_ref.name = copy.deepcopy(self.name, memo)
        copied_var_ref.line = self.line
        copied_var_ref.value = copy.deepcopy(self.value, memo)
        copied_var_ref.type = copy.deepcopy(self.type, memo)
        copied_var_ref.scope = copy.deepcopy(self.scope, memo)

        # Register the copied variable reference in the node registry
        registry = memo.get('registry', None)
        if registry is not None:
            registry['varRef'].append(copied_var_ref)

        return copied_var_ref

    def evaluateType(self):
        if self.type is not None:
            return self.type
        return 'invalid'
        
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
 
    def __eq__(self, other):
        return (isinstance(other, VariableUpdated) and
                self.name == other.name and
                self.value == other.value)
        
    def __str__(self):
        return f"{self.name} = {str(self.value)}"
    
    def __repr__(self):
        return f"VariableUpdated({str(self.name)})"
    
    def __deepcopy__(self, memo):
        cls = self.__class__
        copied_var_updated = cls.__new__(cls)
        memo[id(self)] = copied_var_updated

        copied_var_updated.name = copy.deepcopy(self.name, memo)
        copied_var_updated.value = copy.deepcopy(self.value, memo)
        copied_var_updated.line = self.line

        if copied_var_updated.value is not None:
            copied_var_updated.value.parent = copied_var_updated
            copied_var_updated.value.parent_attr = 'value'

        registry = memo.get('registry', None)
        if registry is not None:
            registry['varUpdate'].append(copied_var_updated)

        return copied_var_updated

    def evaluateType(self):
        if self.value is not None:
            return self.value.evaluateType()
        return "invalid"
        
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
    
    def __deepcopy__(self, memo):
        cls = self.__class__
        copied_func_decl = cls.__new__(cls)
        memo[id(self)] = copied_func_decl

        copied_func_decl.name = copy.deepcopy(self.name, memo)
        copied_func_decl.return_type = copy.deepcopy(self.return_type, memo)
        copied_func_decl.parameters = copy.deepcopy(self.parameters, memo)
        copied_func_decl.block = copy.deepcopy(self.block, memo)
        copied_func_decl.arity = self.arity
        copied_func_decl.line = self.line

        for index, param in enumerate(copied_func_decl.parameters):
            param.parent = copied_func_decl
            param.parent_attr = 'parameters'
            param.parent_index = index

        if copied_func_decl.block is not None:
            copied_func_decl.block.parent = copied_func_decl
            copied_func_decl.block.parent_attr = 'block'

        registry = memo.get('registry', None)
        if registry is not None:
            registry['funcDecl'].append(copied_func_decl)

        return copied_func_decl
    
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
    
    def __str__(self):
        return f"{str(self.value)}"
    
    def __repr__(self):
        return f"Return({repr(self.value)})"

    def __eq__(self, other):
        return isinstance(other, Return) and self.value == other.value
    
    def __deepcopy__(self, memo):
        cls = self.__class__
        copied_return = cls.__new__(cls)
        memo[id(self)] = copied_return

        copied_return.value = copy.deepcopy(self.value, memo)
        copied_return.line = self.line

        if copied_return.value is not None:
            copied_return.value.parent = copied_return
            copied_return.value.parent_attr = 'value'

        registry = memo.get('registry', None)
        if registry is not None:
            registry['return'].append(copied_return)

        return copied_return
    
     
    def evaluateType(self):
        if self.value is not None:
            return self.value.evaluateType()
        return 'invalid'
    
    
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
    
    def __deepcopy__(self, memo):
        cls = self.__class__
        copied_func_call = cls.__new__(cls)
        memo[id(self)] = copied_func_call

        copied_func_call.name = copy.deepcopy(self.name, memo)
        copied_func_call.args = copy.deepcopy(self.args, memo)
        copied_func_call.arity = self.arity
        copied_func_call.line = self.line
        copied_func_call.type = copy.deepcopy(self.type, memo)
        copied_func_call.transformed = copy.deepcopy(self.transformed, memo)

        for index, arg in enumerate(copied_func_call.args):
            arg.parent = copied_func_call
            arg.parent_attr = 'args'
            arg.parent_index = index

        registry = memo.get('registry', None)
        if registry is not None:
            registry['funcCall'].append(copied_func_call)

        return copied_func_call

    def evaluateType(self):
        if self.type is not None:
            return self.type
        return 'invalid'
    
    def accept(self, visitor):
        return visitor.visit_function_call(self)

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
    
    def __deepcopy__(self, memo):
        cls = self.__class__
        copied_argument = cls.__new__(cls)
        memo[id(self)] = copied_argument

        copied_argument.name = copy.deepcopy(self.name, memo)
        copied_argument.value = copy.deepcopy(self.value, memo)
        copied_argument.cached_type = copy.deepcopy(self.cached_type, memo)

        if copied_argument.value is not None and isinstance(copied_argument.value, ASTNode):
            copied_argument.value.parent = copied_argument
            copied_argument.value.parent_attr = "value"

        return copied_argument
  
      
    def evaluateType(self):
        if self.cached_type is not None:
            return self.cached_type
        else:
            return self.value.evaluateType()
    
    
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
    
    def __deepcopy__(self, memo):
        cls = self.__class__
        copied_method_call = cls.__new__(cls)
        memo[id(self)] = copied_method_call

        copied_method_call.receiver = copy.deepcopy(self.receiver, memo)
        copied_method_call.name = copy.deepcopy(self.name, memo)
        copied_method_call.args = copy.deepcopy(self.args, memo)
        copied_method_call.receiverTy = copy.deepcopy(self.receiverTy, memo)
        copied_method_call.line = self.line

        if copied_method_call.receiver is not None:
            copied_method_call.receiver.parent = copied_method_call
            copied_method_call.receiver.parent_attr = 'receiver'
            copied_method_call.receiver.parent_index = None

        for index, arg in enumerate(copied_method_call.args):
            arg.parent = copied_method_call
            arg.parent_attr = 'args'
            arg.parent_index = index

        return copied_method_call
    
    def evaluateType(self):
        if self.return_type is not None:
            return self.return_type
        return 'invalid'
    
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
            self.comparison.parent_index = None

        # Set parent reference and context for the main block
        if self.block is not None:
            self.block.parent = self
            self.block.parent_attr = 'block'
            self.comparison.parent_index = None

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
    
    def __deepcopy__(self, memo):
    
        cls = self.__class__
        copied_if = cls.__new__(cls)
        memo[id(self)] = copied_if
        
        # Deep copy comparison and set parent references
        copied_if.comparison = copy.deepcopy(self.comparison, memo)
        if copied_if.comparison is not None:
            copied_if.comparison.parent = copied_if
            copied_if.comparison.parent_attr = 'comparison'
            copied_if.comparison.parent_index = None  # Not in a list
        
        copied_if.line = self.line
        
        registry = memo.get('registry', None)
        
        # Deep copy block and set parent references
        if self.block is not None:
            copied_if.block = copy.deepcopy(self.block, memo)
            copied_if.block.parent = copied_if
            copied_if.block.parent_attr = 'block'
            copied_if.block.parent_index = None  # Not in a list
        else:
            copied_if.block = None
        
        # Deep copy elifNodes and set parent references
        copied_if.elifNodes = []
        for index, (cond, blk) in enumerate(self.elifNodes):
            copied_cond = copy.deepcopy(cond, memo)
            copied_blk = copy.deepcopy(blk, memo) if blk else None
            if copied_cond:
                copied_cond.parent = copied_if
                copied_cond.parent_attr = 'elif_condition'
                copied_cond.parent_index = index
            if copied_blk:
                copied_blk.parent = copied_if
                copied_blk.parent_attr = 'elif_block'
                copied_blk.parent_index = index
            copied_if.elifNodes.append((copied_cond, copied_blk))
        
        # Deep copy elseBlock and set parent references
        if self.elseBlock is not None:
            copied_if.elseBlock = copy.deepcopy(self.elseBlock, memo)
            copied_if.elseBlock.parent = copied_if
            copied_if.elseBlock.parent_attr = 'elseBlock'
            copied_if.elseBlock.parent_index = None
        else:
            copied_if.elseBlock = None
        
        if registry is not None:
            registry['if'].append(copied_if)
        
        return copied_if
    
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
    
    def __deepcopy__(self, memo):
        cls = self.__class__
        copied_while = cls.__new__(cls)
        memo[id(self)] = copied_while

        copied_while.comparison = copy.deepcopy(self.comparison, memo)
        copied_while.block = copy.deepcopy(self.block, memo)
        copied_while.line = self.line

        if copied_while.comparison is not None:
            copied_while.comparison.parent = copied_while
            copied_while.comparison.parent_attr = 'comparison'
            copied_while.comparison.parent_index = None

        if copied_while.block is not None:
            copied_while.block.parent = copied_while
            copied_while.block.parent_attr = 'block'
            copied_while.block.parent_index = None

        registry = memo.get('registry', None)
        if registry is not None:
            registry['while'].append(copied_while)

        return copied_while
    
    def accept(self, visitor):
        return visitor.visit_while(self)
    
    def print_content(self, indent=0):
        print(" " * indent + "While")
        self.comparison.print_content(indent + 2)
        self.block.print_content(indent + 2)
       
class StringCat(ASTNode):
    def __init__(self, strings, line=None):
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

    def __deepcopy__(self, memo):
        cls = self.__class__
        copied_string_cat = cls.__new__(cls)
        memo[id(self)] = copied_string_cat

        copied_string_cat.strings = copy.deepcopy(self.strings, memo)
        copied_string_cat.line = self.line
        copied_string_cat.evaluated = copy.deepcopy(self.evaluated, memo)
        copied_string_cat.visited = self.visited

        for idx, s in enumerate(copied_string_cat.strings):
            if isinstance(s, String):
                s.parent = copied_string_cat
                s.parent_attr = 'strings'
                s.parent_index = idx

        return copied_string_cat
    
    def evaluateType(self):
        return "string"

    def accept(self, visitor):
        return visitor.visit_string_cat(self)
    
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
    
    def __deepcopy__(self, memo):
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
        self.transformed = None    

    def __str__(self):
        return f"{str(self.left)} '{self.operator}' {str(self.right)}"
 
    def __repr__(self):
        return f"BinaryOp({repr(self.left)} '{self.operator}' {repr(self.right)})"

    def __eq__(self, other):
        return (isinstance(other, BinaryOp) and
                self.left == other.left and
                self.operator == other.operator and
                self.right == other.right)
    
    def __deepcopy__(self, memo):
        cls = self.__class__
        copied_binary_op = cls.__new__(cls)
        memo[id(self)] = copied_binary_op

        copied_binary_op.left = copy.deepcopy(self.left, memo)
        copied_binary_op.operator = copy.deepcopy(self.operator, memo)
        copied_binary_op.right = copy.deepcopy(self.right, memo)
        copied_binary_op.line = self.line
        copied_binary_op.cached_type = copy.deepcopy(self.cached_type, memo)
        copied_binary_op.transformed = copy.deepcopy(self.transformed, memo)

        if copied_binary_op.left is not None:
            copied_binary_op.left.parent = copied_binary_op
            copied_binary_op.left.parent_attr = 'left'

        if copied_binary_op.right is not None:
            copied_binary_op.right.parent = copied_binary_op
            copied_binary_op.right.parent_attr = 'right'

        registry = memo.get('registry', None)
        if registry is not None:
            registry['binOp'].append(copied_binary_op)

        return copied_binary_op
    
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

    def print_content(self, indent=0):
        print(" " * indent + f"BinaryOp (Operator {self.operator})")
        self.left.print_content(indent + 2)
        self.right.print_content(indent + 2)

# for < > <= >= == !=
class Comparison(Expression):
    def __init__(self, left, operator, right, line=None):
        super().__init__(left, operator, right, line)
        self._cached_type = None
  
    def __str__(self):
        return f"{str(self.left)} '{self.operator}' {str(self.right)}"
    
    def __repr__(self):
        return f"Comparison({repr(self.left)} '{self.operator}' {repr(self.right)})"
    
    def __eq__(self, other):
        return (isinstance(other, Comparison) and
                self.left == other.left and
                self.operator == other.operator and
                self.right == other.right)
    
    def __deepcopy__(self, memo):
        cls = self.__class__
        copied_comparison = cls.__new__(cls)
        memo[id(self)] = copied_comparison

        copied_comparison.left = copy.deepcopy(self.left, memo)
        copied_comparison.operator = copy.deepcopy(self.operator, memo)
        copied_comparison.right = copy.deepcopy(self.right, memo)
        copied_comparison.line = self.line
        copied_comparison._cached_type = copy.deepcopy(self._cached_type, memo)

        if copied_comparison.left is not None:
            copied_comparison.left.parent = copied_comparison
            copied_comparison.left.parent_attr = 'left'

        if copied_comparison.right is not None:
            copied_comparison.right.parent = copied_comparison
            copied_comparison.right.parent_attr = 'right'

        registry = memo.get('registry', None)
        if registry is not None:
            registry['comparison'].append(copied_comparison)

        return copied_comparison

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
    
    def print_content(self, indent=0):
        print(" " * indent + f"Comparison (Operator: {self.operator})")
        self.left.print_content(indent + 2)
        self.right.print_content(indent + 2)

# for && ||
class LogicalOp(Expression):
    def __init__(self, left, operator, right, line= None):
        super().__init__(left, operator, right, line)
        self._cached_type = None

    def __str__(self):
        return f"'{str(self.left)}' '{self.operator}' '{str(self.right)}'"
    
    def __repr__(self):
        return f"LogicalOp('{repr(self.left)}' '{self.operator}' '{repr(self.right)}')"

    def __eq__(self, other):
        return (isinstance(other, LogicalOp) and
                self.left == other.left and
                self.operator == other.operator and
                self.right == other.right)
    
    def __deepcopy__(self, memo):
        cls = self.__class__
        copied_logical_op = cls.__new__(cls)
        memo[id(self)] = copied_logical_op

        copied_logical_op.left = copy.deepcopy(self.left, memo)
        copied_logical_op.operator = copy.deepcopy(self.operator, memo)
        copied_logical_op.right = copy.deepcopy(self.right, memo)
        copied_logical_op.line = self.line
        copied_logical_op._cached_type = copy.deepcopy(self._cached_type, memo)

        if copied_logical_op.left is not None:
            copied_logical_op.left.parent = copied_logical_op
            copied_logical_op.left.parent_attr = 'left'

        if copied_logical_op.right is not None:
            copied_logical_op.right.parent = copied_logical_op
            copied_logical_op.right.parent_attr = 'right'

        registry = memo.get('registry', None)
        if registry is not None:
            registry['logOp'].append(copied_logical_op)

        return copied_logical_op
    
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
    
    def print_content(self, indent=0):
        print(" " * indent + f"LogicalOp (Operator: {self.operator})")
        self.left.print_content(indent + 2)
        self.right.print_content(indent + 2)        
   
# for -5 / +5 and !
class UnaryOp(Expression):
    def __init__(self, operator, left, line=None):
        super().__init__(left, operator, None, line)
        self._cached_type = None
        if self.left is not None:
            self.left.parent = self
            self.left.parent_attr = 'left'

    def __str__(self):
        return f"'{self.operator}{self.left}'"

    def __repr__(self):
        return f"UnaryOp({self.operator}{repr(self.left)})"

    def __eq__(self, other):
        return (isinstance(other, UnaryOp) and
                self.operator == other.operator and
                self.left == other.left)

    def __deepcopy__(self, memo):
        cls = self.__class__
        copied_unary_op = cls.__new__(cls)
        memo[id(self)] = copied_unary_op

        copied_unary_op.operator = copy.deepcopy(self.operator, memo)
        copied_unary_op.left = copy.deepcopy(self.left, memo)
        copied_unary_op.line = self.line
        copied_unary_op._cached_type = copy.deepcopy(self._cached_type, memo)

        if copied_unary_op.left is not None:
            copied_unary_op.left.parent = copied_unary_op
            copied_unary_op.left.parent_attr = 'left'

        return copied_unary_op
    
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
    
    def print_content(self, indent=0):
        print(" " * indent + f"UnaryOp (Operator: {self.operator})")
        self.left.print_content(indent + 2)

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