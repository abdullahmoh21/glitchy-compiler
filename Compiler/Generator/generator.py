from Compiler.utils import *
import llvmlite.ir as ir

class LLVMCodeGenerator:
    def __init__(self, symbol_table):
        self.symbol_table = symbol_table
        self.module = ir.Module(name="module")
        self.module.globals = {}
        self.builder = None
        self.function = None
        self.string_counter = 0
        self.current_after_while_block = None
        self.builtin_dispatcher = {
            'input': self.input_builtin,
            'print': self.print_builtin,
        }

    def generate_code(self, node):
        if has_error_occurred():
            return None

        func_type = ir.FunctionType(ir.VoidType(), [])
        self.function = ir.Function(self.module, func_type, name="main")
        block = self.function.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)
        
        try:
            node.accept(self)
        except ExitSignal:
            return
        if not self.builder.block.is_terminated:
            self.builder.ret_void()

        return self.module

    def visit_program(self, node):
        try:
            for statement in node.statements:
                statement.accept(self)
        except ExitSignal:
            return
        except Exception as e:
            throw(CompilationError(f"An unknown error occurred during code generation. {e}"))

    def visit_block(self, node):
        self.symbol_table.enterScope()
        for statement in node.statements:
            statement.accept(self)
        self.symbol_table.exitScope()

    def visit_variable(self, node):
        if isinstance(node, VariableDeclaration):
            mangled_name = self.symbol_table.getMangledName(node.name)
            if mangled_name is None:
                mangled_name = node.name
            value = node.value.accept(self)
            var_type = value.type

            # Allocate space for the variable within the current function
            local_var = self.builder.alloca(var_type, name=mangled_name)
            self.builder.store(value, local_var)
            self.symbol_table.setReference(node.name, local_var)

        elif isinstance(node, VariableUpdated):
            mangled_name = self.symbol_table.getMangledName(node.name)
            if mangled_name is None:
                raise Error(f"Could not retrieve mangled name for '{node.name}' from symbol table")
            value = node.value.accept(self)
            expected_type = self.getIrType(self.symbol_table.getType(node.name))
            local_var = self.symbol_table.getReference(node.name)

            if local_var is None:
                raise Error(f"Variable '{node.name}' referenced before declaration or update")
            if value.type != expected_type:
                if value.type == ir.DoubleType() and expected_type == ir.IntType(64):
                    report(f"Precision loss. Truncating double to int for Variable '{node.name}'.","Warning",error=False,line=node.line)
                    value = self.builder.fptosi(value, ir.IntType(64))
                elif value.type == ir.IntType(64) and expected_type == ir.DoubleType():
                    value = self.builder.sitofp(value, ir.DoubleType())
                else:
                    throw(TypeError(f"Invalid assignment for symbol '{node.name}'. expected '{expected_type}', got: '{value.type}'"))
            self.builder.store(value, local_var)

        elif isinstance(node, VariableReference):
            mangled_name = self.symbol_table.getMangledName(node.name)
            if mangled_name is None:  # If no mangled name, assume it's a function parameter
                mangled_name = node.name

            reference = self.symbol_table.getReference(node.name)
            if reference is None:
                throw(Error(f"Variable '{node.name}' referenced before declaration"))

            if isinstance(reference, ir.AllocaInstr):
                return self.builder.load(reference, name=mangled_name)
            else:
                # For function parameters
                return reference

    def visit_if(self, node):
        cond_val = node.comparison.accept(self)

        if_true_block = self.builder.append_basic_block(name="if_true_branch")
        if_false_block = self.builder.append_basic_block(name="if_false_branch")

        needs_merge_block = False  # Track if we need a merge block
        merge_block = None  # Define merge block only when needed

        self.builder.cbranch(cond_val, if_true_block, if_false_block)

        def insertNop():
            if self.builder.block.is_terminated and len(self.builder.block.instructions) == 1:
                self.builder.comment("Nop")
                zero = ir.Constant(ir.IntType(64), 0)
                self.builder.position_before(self.builder.block.instructions[0])
                self.builder.add(zero, zero)

        # True Branch
        self.builder.position_at_end(if_true_block)
        node.block.accept(self)
        insertNop()
        if not self.builder.block.is_terminated:
            needs_merge_block = True
            if not merge_block:
                merge_block = self.builder.append_basic_block(name="if_merge")
            self.builder.branch(merge_block)

        # False Branch / Elif / Else Handling
        self.builder.position_at_end(if_false_block)

        if len(node.elifNodes) > 0:
            for i, elif_node in enumerate(node.elifNodes):
                elif_cond_val = elif_node[0].accept(self)

                elif_true_block = self.builder.append_basic_block(name=f"elif{i}_true_branch")
                elif_false_block = self.builder.append_basic_block(name=f"elif{i}_false_branch")

                self.builder.cbranch(elif_cond_val, elif_true_block, elif_false_block)

                self.builder.position_at_end(elif_true_block)
                elif_node[1].accept(self)
                insertNop()
                if not self.builder.block.is_terminated:
                    needs_merge_block = True
                    if not merge_block:
                        merge_block = self.builder.append_basic_block(name="if_merge")
                    self.builder.branch(merge_block)

                self.builder.position_at_end(elif_false_block)

            # Handle the final `else` block if it exists
            if node.elseBlock is not None:
                node.elseBlock.accept(self)
                insertNop()
                if not self.builder.block.is_terminated:
                    needs_merge_block = True
                    if not merge_block:
                        merge_block = self.builder.append_basic_block(name="if_merge")
                    self.builder.branch(merge_block)
            else:
                insertNop()
                if not self.builder.block.is_terminated:
                    needs_merge_block = True
                    if not merge_block:
                        merge_block = self.builder.append_basic_block(name="if_merge")
                    self.builder.branch(merge_block)

        elif node.elseBlock is not None:
            # Directly handle the else block if there are no elifs
            node.elseBlock.accept(self)
            insertNop()
            if not self.builder.block.is_terminated:
                needs_merge_block = True
                if not merge_block:
                    merge_block = self.builder.append_basic_block(name="if_merge")
                self.builder.branch(merge_block)
        else:
            insertNop()
            if not self.builder.block.is_terminated:
                needs_merge_block = True
                if not merge_block:
                    merge_block = self.builder.append_basic_block(name="if_merge")
                self.builder.branch(merge_block)

        # Final Merge Block
        if needs_merge_block:
            self.builder.position_at_end(merge_block)

    def visit_while(self, node):
        while_cond_block = self.builder.append_basic_block(name="while_cond")
        while_body_block = self.builder.append_basic_block(name="while_body")
        after_while_block = self.builder.append_basic_block(name="after_while")

        # for break statements
        previous_after_while_block = self.current_after_while_block
        self.current_after_while_block = after_while_block

        self.builder.branch(while_cond_block)

        self.builder.position_at_end(while_cond_block)
        cond_val = node.comparison.accept(self)
        self.builder.cbranch(cond_val, while_body_block, after_while_block)

        self.builder.position_at_end(while_body_block)
        node.block.accept(self)

        if not self.builder.block.is_terminated:
            self.builder.branch(while_cond_block)  # Recheck the condition after each loop

        self.builder.position_at_end(after_while_block)
        self.current_after_while_block = previous_after_while_block

    def visit_break(self, node):
        after_while_block = self.current_after_while_block
        self.builder.branch(after_while_block)

    def visit_function_declaration(self, function):
        return_type = self.getIrType(function.return_type)
        param_types = [self.getIrType(param.type) for param in function.parameters]
        func_type = ir.FunctionType(return_type, param_types)

        func = ir.Function(self.module, func_type, name=function.name)
        entry_block = func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(entry_block)

        self.symbol_table.enterScope()

        for i, param in enumerate(function.parameters):
            param_value = func.args[i]
            param_value.name = param.name
            param_alloca = self.builder.alloca(self.getIrType(param.type), name=param.name)
            self.builder.store(param_value, param_alloca)
            self.symbol_table.setReference(param.name, param_alloca)

        self.builder.position_at_end(entry_block)

        for statement in function.block.statements:
            statement.accept(self)

        if not self.builder.block.is_terminated:
            if func.ftype.return_type == ir.VoidType():
                self.builder.ret_void()
            else:
                throw(ReturnError(f"The function '{function.name}' expects a return type of '{function.return_type}'. Please ensure the function is properly terminated. "))
        self.symbol_table.exitScope()

        # reset builders pointer to main function
        if 'main' in self.module.globals:
            main_func = self.module.get_global("main")
            main_block = main_func.entry_basic_block
            self.builder = ir.IRBuilder(main_block)

    def visit_return(self, node):
        if not isinstance(node.value, Null):
            return_value = node.value.accept(self)
            if not isinstance(return_value, ir.Instruction) and return_value.is_pointer:
                return_value = self.builder.load(return_value)

            if not self.builder.block.is_terminated:
                self.builder.ret(return_value)
        else:
            if not self.builder.block.is_terminated:
                self.builder.ret_void()

    def visit_function_call(self, node):
        if node.name in self.builtin_dispatcher:
            return self.builtin_dispatcher[node.name](node)

        func = self.module.get_global(node.name)
        args = [arg.value.accept(self) for arg in node.args]
        call_result = self.builder.call(func, args)

        return_type_str = self.symbol_table.getFunctionType(node.name)
        return_type = self.getIrType(return_type_str)

        if return_type != ir.VoidType():
            return call_result
        else:
            return None

    def visit_method_call(self, node):
        if isinstance(node.receiver, MethodCall):
            result = self.visit_method_call(node.receiver)
        else:
            result = node.receiver.accept(self)

        method = MethodTable.get(node.receiverTy, node.name)
        if method is None:
            throw(CompilationError(f"Method '{node.name}' does not exist for type '{node.receiverTy}'"))

        method_name = f"{node.name}_call"
        if method_name in self.__class__.__dict__:
            return getattr(self, method_name)(node, result)
        else:
            throw(NotImplementedError(f"Method '{method_name}' is not implemented in the generator."))

    def visit_binary_op(self, node):
        left = node.left.accept(self)
        right = node.right.accept(self)
        left_type = left.type
        right_type = right.type

        result = None

        if left_type == ir.IntType(64) and right_type == ir.IntType(64):
            if node.operator == '+':
                result = self.builder.add(left, right)
            elif node.operator == '-':
                result = self.builder.sub(left, right)
            elif node.operator == '*':
                result = self.builder.mul(left, right)
            elif node.operator == '/':
                result = self.builder.sdiv(left, right)
            elif node.operator == '%':
                result = self.builder.srem(left, right)
            elif node.operator == '^':
                self.declareGlobal('pow')
                pow_ = self.module.get_global('pow')
                left = self.builder.sitofp(left, ir.DoubleType())
                right = self.builder.sitofp(right, ir.DoubleType())
                result = self.builder.call(pow_, [left, right])
            else:
                throw(CompilationError(f"Unknown operator for integers: {node.operator}"))

        elif left_type == ir.DoubleType() and right_type == ir.DoubleType():
            if node.operator == '+':
                result = self.builder.fadd(left, right)
            elif node.operator == '-':
                result = self.builder.fsub(left, right)
            elif node.operator == '*':
                result = self.builder.fmul(left, right)
            elif node.operator == '/':
                result = self.builder.fdiv(left, right)
            elif node.operator == '%':
                result = self.builder.frem(left, right)
            elif node.operator == '^':
                self.declareGlobal('pow')
                pow_ = self.module.get_global('pow')
                result = self.builder.call(pow_, [left, right])
            else:
                throw(CompilationError(f"Unknown operator for doubles: {node.operator}"))

        elif (left_type == ir.IntType(64) and right_type == ir.DoubleType()) or (left_type == ir.DoubleType() and right_type == ir.IntType(64)):
            # most type promotions are done in the analyzer. this is for values that are unknown until runtime
            if left_type == ir.IntType(64):
                left = self.builder.sitofp(left, ir.DoubleType())
            elif right_type == ir.IntType(64):
                right = self.builder.sitofp(right, ir.DoubleType())

            if node.operator == '+':
                result = self.builder.fadd(left, right)
            elif node.operator == '-':
                result = self.builder.fsub(left, right)
            elif node.operator == '*':
                result = self.builder.fmul(left, right)
            elif node.operator == '/':
                result = self.builder.fdiv(left, right)
            elif node.operator == '%':
                result = self.builder.frem(left, right)
            elif node.operator == '^':
                self.declareGlobal('pow')
                pow_ = self.module.get_global('pow')
                result = self.builder.call(pow_, [left, right])
            else:
                throw(CompilationError(f"Unknown operator for mixed types: {node.operator}"))

        else:
            throw(CompilationError(f"Illegal Binary Operation on line {node.line}: \n\t{str(node)}\nCannot perform binary operations on differing or unsupported types: {left_type} and {right_type}"))

        return result

    def visit_unary_op(self, node):
        operand = node.left.accept(self)

        if node.operator == '-':
            if operand.type == ir.DoubleType():
                result = self.builder.fneg(operand)
            elif operand.type == ir.IntType(64):
                result = self.builder.neg(operand)
            else:
                throw(CompilationError(f"Unknown operand for unary operation: {node.operand}"))
        elif node.operator == '!':
            result = self.builder.not_(operand)
        elif node.operator == '+':
            result = operand
        else:
            throw(ValueError(f"Unknown operator: {node.operator}"))

        return result

    def visit_comparison(self, node):
        left = node.left.accept(self)
        right = node.right.accept(self)
        left_type = left.type
        right_type = right.type

        # String comparisons
        if node.left.evaluateType() == 'string' and node.operator == '==':
            self.declareGlobal('strcmp')
            strcmp_func = self.module.globals['strcmp']
            strcmp_result = self.builder.call(strcmp_func, [left, right])
            result = self.builder.icmp_signed('==', strcmp_result, ir.Constant(ir.IntType(64), 0))  # strcmp returns 0 if strings are equal
            return result

        if left_type == ir.IntType(64) and right_type == ir.IntType(64):
            if node.operator == '==':
                result = self.builder.icmp_signed('==', left, right)
            elif node.operator == '!=':
                result = self.builder.icmp_signed('!=', left, right)
            elif node.operator == '<':
                result = self.builder.icmp_signed('<', left, right)
            elif node.operator == '<=':
                result = self.builder.icmp_signed('<=', left, right)
            elif node.operator == '>':
                result = self.builder.icmp_signed('>', left, right)
            elif node.operator == '>=':
                result = self.builder.icmp_signed('>=', left, right)
            else:
                throw(ValueError(f"Unknown operator: {node.operator}"))

        elif left_type == ir.IntType(1) and right_type == ir.IntType(1):
            if node.operator == '==':
                result = self.builder.icmp_signed('==', left, right)
            elif node.operator == '!=':
                result = self.builder.icmp_signed('!=', left, right)
            elif node.operator == '<':
                result = self.builder.icmp_signed('<', left, right)
            elif node.operator == '<=':
                result = self.builder.icmp_signed('<=', left, right)
            elif node.operator == '>':
                result = self.builder.icmp_signed('>', left, right)
            elif node.operator == '>=':
                result = self.builder.icmp_signed('>=', left, right)
            else:
                throw(ValueError(f"Unknown operator: {node.operator}"))

        elif left_type == ir.DoubleType() and right_type == ir.DoubleType():
            if node.operator == '==':
                result = self.builder.fcmp_ordered('==', left, right)
            elif node.operator == '!=':
                result = self.builder.fcmp_ordered('!=', left, right)
            elif node.operator == '<':
                result = self.builder.fcmp_ordered('<', left, right)
            elif node.operator == '<=':
                result = self.builder.fcmp_ordered('<=', left, right)
            elif node.operator == '>':
                result = self.builder.fcmp_ordered('>', left, right)
            elif node.operator == '>=':
                result = self.builder.fcmp_ordered('>=', left, right)
            else:
                throw(ValueError(f"Unknown operator: {node.operator}"))

        elif (left_type == ir.IntType(64) and right_type == ir.DoubleType()) or (left_type == ir.DoubleType() and right_type == ir.IntType(64)):
            if left_type == ir.IntType(64):
                left = self.builder.sitofp(left, ir.DoubleType())
            elif right_type == ir.IntType(64):
                right = self.builder.sitofp(right, ir.DoubleType())

            if node.operator == '==':
                result = self.builder.fcmp_ordered('==', left, right)
            elif node.operator == '!=':
                result = self.builder.fcmp_ordered('!=', left, right)
            elif node.operator == '<':
                result = self.builder.fcmp_ordered('<', left, right)
            elif node.operator == '<=':
                result = self.builder.fcmp_ordered('<=', left, right)
            elif node.operator == '>':
                result = self.builder.fcmp_ordered('>', left, right)
            elif node.operator == '>=':
                result = self.builder.fcmp_ordered('>=', left, right)
            else:
                throw(ValueError(f"Unknown operator: {node.operator}"))

        else:
            throw(CompilationError(f"Cannot perform operation on differing or unsupported types on line {node.line}: {str(node)} with types '{node.left.evaluateType()}' '{node.operator}' '{node.evaluateType()}'"))
        return result

    def visit_logical_op(self, node):
        left = node.left.accept(self)
        right = node.right.accept(self)

        if node.operator == '&&':
            result = self.builder.and_(left, right)
        elif node.operator == '||':
            result = self.builder.or_(left, right)
        else:
            throw(ValueError(f"Unknown operator: {node.operator}"))

        return result

    def visit_string_cat(self, node):
        if node.evaluated is not None:
            return self.visit_string(node.evaluated)

        if len(node.strings) == 0:
            raise CompilationError("No strings to concatenate")

        # Declare global functions
        self.declareGlobal('strcat')
        self.declareGlobal('sprintf')
        self.declareGlobal('strlen')
        self.declareGlobal('memset')

        global_buffer = self.module.get_global("global_string_buffer")
        buffer_ptr = self.builder.bitcast(global_buffer, ir.PointerType(ir.IntType(8)))
        self.resetBuffer(buffer_ptr, 8192)

        result_ptr = buffer_ptr
        for i in range(len(node.strings)):
            if isinstance(node.strings[i], str):
                next_string = String(node.strings[i]).accept(self)
            else:
                next_string = node.strings[i].accept(self)

            # Check the type and convert if necessary
            if not (isinstance(next_string.type, ir.PointerType) and next_string.type.pointee == ir.IntType(8)):
                if next_string.type is ir.IntType(64):
                    format_str_int = self.builder.bitcast(self.module.get_global('sprintf_fmt_int'), ir.PointerType(ir.IntType(8)))
                    buffer_int = self.builder.alloca(ir.ArrayType(ir.IntType(8), 22))
                    buffer_int_ptr = self.builder.bitcast(buffer_int, ir.PointerType(ir.IntType(8)))
                    self.builder.call(self.module.get_global('sprintf'), [buffer_int_ptr, format_str_int, next_string])
                    next_string = buffer_int_ptr
                elif next_string.type is ir.DoubleType():
                    format_str_double = self.builder.bitcast(self.module.get_global('sprintf_fmt_double'), ir.PointerType(ir.IntType(8)))
                    buffer_double = self.builder.alloca(ir.ArrayType(ir.IntType(8), 32))
                    buffer_double_ptr = self.builder.bitcast(buffer_double, ir.PointerType(ir.IntType(8)))
                    self.builder.call(self.module.get_global('sprintf'), [buffer_double_ptr, format_str_double, next_string])
                    next_string = buffer_double_ptr
                elif next_string.type is ir.IntType(1):  # Boolean type (i1)
                    true_str = self.builder.global_string_ptr("true", name="bool_true")
                    false_str = self.builder.global_string_ptr("false", name="bool_false")
                    next_string = self.builder.select(next_string, true_str, false_str)
                else:
                    throw(CompilationError(f"An error occurred during the code generation of the string concatenation: '{str(node)}'"))

            strcat = self.module.get_global('strcat')
            self.builder.call(strcat, [result_ptr, next_string])

            # Move result_ptr to /00
            result_ptr = self.builder.gep(result_ptr, [self.builder.call(self.module.get_global('strlen'), [next_string])])

        return buffer_ptr

    def visit_integer(self, node):
        const_val = ir.Constant(ir.IntType(64), node.value)
        int_var = self.builder.alloca(const_val.type, name="int_var")
        self.builder.store(const_val, int_var)
        return self.builder.load(int_var)

    def visit_double(self, node):
        const_val = ir.Constant(ir.DoubleType(), node.value)
        node.name = self.builder.alloca(const_val.type, name="node.name")
        self.builder.store(const_val, node.name)
        return self.builder.load(node.name)

    def visit_boolean(self, node):
        const_val = ir.Constant(ir.IntType(1), node.value)
        bool_var = self.builder.alloca(const_val.type, name="bool_var")
        self.builder.store(const_val, bool_var)
        return self.builder.load(bool_var)

    def visit_string(self, node):
        str_val = bytearray(node.value.encode("utf8")) + b"\0"
        str_constant = ir.Constant(ir.ArrayType(ir.IntType(8), len(str_val)), str_val)

        unique_name = f"str_{self.string_counter}"
        self.string_counter += 1

        str_var = self.builder.alloca(str_constant.type, name=unique_name)
        self.builder.store(str_constant, str_var)
        str_ptr = self.builder.gep(str_var, [ir.Constant(ir.IntType(64), 0), ir.Constant(ir.IntType(64), 0)])

        return self.builder.bitcast(str_ptr, ir.PointerType(ir.IntType(8)))

    def visit_null(self, node):
        return ir.Constant(ir.IntType(64), None)

# --------------------------- Helpers --------------------------- #

    def declareGlobal(self, name):
        """ Declares a global if it hasn't been declared already """

        format_strings = {
            "printf": {
                "print_fmt_int": "%lld\n\00",
                "print_fmt_double": "%f\n\00",
                "print_fmt_bool": "%s\n\00",
                "print_fmt_str": "%s\n\00"
            },
            "scanf": {
                "format_scanf": "%s\00"
            },
            "sprintf": {
                "sprintf_fmt_int": "%lld\00",
                "sprintf_fmt_double": "%f\00"
            }
        }

        if name == "freopen":
            try:
                self.module.get_global("freopen")
            except KeyError:
                freopen_func_type = ir.FunctionType(
                    ir.IntType(8).as_pointer(),
                    [ir.IntType(8).as_pointer(), ir.IntType(8).as_pointer(), ir.IntType(8).as_pointer()]
                )
                ir.Function(self.module, freopen_func_type, name="freopen")

                output_file = "output.bsdk"
                try:
                    self.module.get_global("file_name")
                except KeyError:
                    file_name = ir.GlobalVariable(
                        self.module,
                        ir.ArrayType(ir.IntType(8), len(output_file) + 1),
                        name="file_name"
                    )
                    file_name.initializer = ir.Constant(
                        ir.ArrayType(ir.IntType(8), len(output_file) + 1),
                        bytearray(output_file.encode('utf-8') + b'\00')
                    )

                try:
                    self.module.get_global("mode")
                except KeyError:
                    mode = ir.GlobalVariable(
                        self.module,
                        ir.ArrayType(ir.IntType(8), 2),
                        name="mode"
                    )
                    mode.initializer = ir.Constant(
                        ir.ArrayType(ir.IntType(8), 2),
                        bytearray(b"w\00")
                    )

                try:
                    self.module.get_global("stdout")
                except KeyError:
                    stdout_var = ir.GlobalVariable(self.module, ir.IntType(8).as_pointer(), name="stdout")
                    stdout_var.linkage = 'external'
                    
        if name == "printf":
            for fmt_name, fmt in format_strings["printf"].items():
                try:
                    self.module.get_global(fmt_name)
                except KeyError:
                    c_format_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(fmt)), bytearray(fmt.encode("utf8")))
                    format_global = ir.GlobalVariable(self.module, c_format_str.type, name=fmt_name)
                    format_global.global_constant = True
                    format_global.initializer = c_format_str

            try:
                self.module.get_global("printf")
            except KeyError:
                printf_ty = ir.FunctionType(ir.IntType(64), [ir.PointerType(ir.IntType(8))], var_arg=True)
                ir.Function(self.module, printf_ty, name="printf")
            try:
                self.module.get_global("true_str")
            except KeyError:
                true_str_value = bytearray("true".encode("utf8")) + bytearray([0])  # Add null terminator
                true_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(true_str_value)), true_str_value)
                true_global = ir.GlobalVariable(self.module, true_str.type, name="true_str")
                true_global.global_constant = True
                true_global.initializer = true_str
            try:
                self.module.get_global("false_str")
            except KeyError:
                false_str_value = bytearray("false".encode("utf8")) + bytearray([0])  # Add null terminator
                false_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(false_str_value)), false_str_value)
                false_global = ir.GlobalVariable(self.module, false_str.type, name="false_str")
                false_global.global_constant = True
                false_global.initializer = false_str

        elif name == "scanf":
            format_str_name = "format_scanf"
            try:
                self.module.get_global(format_str_name)
            except KeyError:
                format_str = format_strings["scanf"][format_str_name]
                c_format_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(format_str)), bytearray(format_str.encode("utf8")))
                c_format_str_global = ir.GlobalVariable(self.module, c_format_str.type, name=format_str_name)
                c_format_str_global.linkage = 'internal'
                c_format_str_global.global_constant = True
                c_format_str_global.initializer = c_format_str

            try:
                self.module.get_global("scanf")
            except KeyError:
                scanf_ty = ir.FunctionType(ir.IntType(64), [ir.PointerType(ir.IntType(8))], var_arg=True)
                ir.Function(self.module, scanf_ty, name="scanf")

            try:
                self.module.get_global("global_input_buffer")
            except KeyError:
                buffer_size = 8192
                buffer_ty = ir.ArrayType(ir.IntType(8), buffer_size)
                global_buffer = ir.GlobalVariable(
                    self.module,
                    buffer_ty,
                    name="global_input_buffer"
                )
                global_buffer.linkage = 'internal'
                global_buffer.initializer = ir.Constant(buffer_ty, None)

        elif name == "sprintf":
            for fmt_name, fmt in format_strings["sprintf"].items():
                try:
                    self.module.get_global(fmt_name)
                except KeyError:
                    c_format_str = ir.Constant(ir.ArrayType(ir.IntType(8), len(fmt)), bytearray(fmt.encode("utf8")))
                    format_global = ir.GlobalVariable(self.module, c_format_str.type, name=fmt_name)
                    format_global.global_constant = True
                    format_global.initializer = c_format_str

            try:
                self.module.get_global("sprintf")
            except KeyError:
                sprintf_ty = ir.FunctionType(
                    ir.IntType(64),
                    [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8))],
                    var_arg=True
                )
                ir.Function(self.module, sprintf_ty, name="sprintf")

        elif name == "pow":
            try:
                self.module.get_global("pow")
            except KeyError:
                pow_ty = ir.FunctionType(ir.DoubleType(), [ir.DoubleType(), ir.DoubleType()])
                ir.Function(self.module, pow_ty, name="pow")

        elif name == "strlen":
            try:
                self.module.get_global("strlen")
            except KeyError:
                strlen_ty = ir.FunctionType(ir.IntType(64), [ir.PointerType(ir.IntType(8))])
                ir.Function(self.module, strlen_ty, name="strlen")

        elif name == "strcmp":
            try:
                self.module.get_global("strcmp")
            except KeyError:
                strcmp_ty = ir.FunctionType(ir.IntType(64), [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8))])
                ir.Function(self.module, strcmp_ty, name="strcmp")

        elif name == "strcat":
            try:
                self.module.get_global("strcat")
            except KeyError:
                strcat_ty = ir.FunctionType(ir.PointerType(ir.IntType(8)), [ir.PointerType(ir.IntType(8)), ir.PointerType(ir.IntType(8))])
                ir.Function(self.module, strcat_ty, name="strcat")

            try:
                self.module.get_global("global_string_buffer")
            except KeyError:
                buffer_size = 8192
                buffer_ty = ir.ArrayType(ir.IntType(8), buffer_size)
                global_buffer = ir.GlobalVariable(
                    self.module,
                    buffer_ty,
                    name="global_string_buffer"
                )
                global_buffer.linkage = 'internal'
                global_buffer.initializer = ir.Constant(buffer_ty, None)

        elif name == "atoi":
            try:
                self.module.get_global("atoi")
            except KeyError:
                atoi_ty = ir.FunctionType(ir.IntType(64), [ir.PointerType(ir.IntType(8))])
                ir.Function(self.module, atoi_ty, name="atoi")

        elif name == "atof":
            try:
                self.module.get_global("atof")
            except KeyError:
                atof_ty = ir.FunctionType(ir.DoubleType(), [ir.PointerType(ir.IntType(8))])
                ir.Function(self.module, atof_ty, name="atof")

    def getIrType(self, type_str):
        if type_str == 'integer':
            return ir.IntType(64)
        elif type_str == 'double':
            return ir.DoubleType()
        elif type_str == 'string':
            return ir.PointerType(ir.IntType(8))
        elif type_str == 'boolean':
            return ir.IntType(1)
        elif type_str == 'void':
            return ir.VoidType()
        else:
            throw(ValueError(f"Unknown type: {type_str}"))

    def resetBuffer(self, buffer_ptr, buffer_size):
        try:
            memset = self.module.get_global("memset")
        except KeyError:
            memset_ty = ir.FunctionType(ir.PointerType(ir.IntType(8)), [
                ir.PointerType(ir.IntType(8)),  # dest
                ir.IntType(8),                 # value
                ir.IntType(64)                 # size (in bytes), use i32 for consistency
            ])
            memset = ir.Function(self.module, memset_ty, name="memset")

        buffer_ptr = self.builder.bitcast(buffer_ptr, ir.PointerType(ir.IntType(8)))
        zero = ir.Constant(ir.IntType(8), 0)
        buffer_size_const = ir.Constant(ir.IntType(64), buffer_size)
        self.builder.call(memset, [buffer_ptr, zero, buffer_size_const])

# --------------------------- Builtin functions--------------------------- #
    def print_builtin(self, node):
        expr_value = node.args[0].value.accept(self)
        expr_type = node.args[0].value.evaluateType()

        if expr_value.type == ir.IntType(64):
            format_str_name = "print_fmt_int"
        elif expr_value.type == ir.DoubleType():
            format_str_name = "print_fmt_double"
        elif expr_value.type == ir.IntType(1):
            format_str_name = "print_fmt_bool"
        elif isinstance(expr_value.type, ir.PointerType) and (expr_value.type.pointee == ir.IntType(8) or expr_value.type.pointee == ir.ArrayType(ir.IntType(8), 8192)):
            format_str_name = "print_fmt_str"
        else:
            raise Exception(f"Unsupported expression type: {expr_type}")

        self.declareGlobal('printf')
        fmt_ptr = self.builder.bitcast(self.module.get_global(format_str_name), ir.PointerType(ir.IntType(8)))
        printf = self.module.get_global('printf')

        if expr_type in ['integer', 'double']:
            self.builder.call(printf, [fmt_ptr, expr_value])
        elif expr_type == 'string':
            expr_value = self.builder.bitcast(expr_value, ir.PointerType(ir.IntType(8)))
            self.builder.call(printf, [fmt_ptr, expr_value])
        elif expr_type == 'boolean':
            # Runtime mapping of 1 to "true" and 0 to "false"
            true_str = self.module.get_global("true_str")
            false_str = self.module.get_global("false_str")

            if_true_block = self.builder.append_basic_block(name="if_true_branch")
            if_false_block = self.builder.append_basic_block(name="if_false_branch")
            merge_block = self.builder.append_basic_block(name="if_merge")

            self.builder.cbranch(expr_value, if_true_block, if_false_block)

            self.builder.position_at_end(if_true_block)
            self.builder.call(printf, [fmt_ptr, self.builder.bitcast(true_str, ir.PointerType(ir.IntType(8)))])  
            self.builder.branch(merge_block)  

            self.builder.position_at_end(if_false_block)
            self.builder.call(printf, [fmt_ptr, self.builder.bitcast(false_str, ir.PointerType(ir.IntType(8)))])  

            self.builder.branch(merge_block)  

            self.builder.position_at_end(merge_block)
        else:
            raise Exception(f"Unsupported print type: {expr_type}")

    def input_builtin(self, node):
        self.declareGlobal('scanf')
        c_format_str_global = self.module.get_global('format_scanf')
        fmt_ptr = self.builder.bitcast(c_format_str_global, ir.PointerType(ir.IntType(8)))

        # Input Buffer
        input_buffer = self.module.get_global("global_input_buffer")
        buffer_ptr = self.builder.bitcast(input_buffer, ir.PointerType(ir.IntType(8)))
        self.resetBuffer(buffer_ptr, 8192)

        scanf = self.module.get_global('scanf')
        self.builder.call(scanf, [fmt_ptr, buffer_ptr])
        return buffer_ptr

# -------------------------- Member methods --------------------------- #

    def toInteger_call(self, node, receiver_result):
        self.declareGlobal('atoi')
        atoi_func = self.module.globals['atoi']

        if receiver_result.type != ir.PointerType(ir.IntType(8)):
            throw(TypeError(f"Expected string, got {receiver_result.type} in 'toInteger' call at line {node.line}"))

        result = self.builder.call(atoi_func, [receiver_result])
        return result

    def toDouble_call(self, node, receiver_result):
        self.declareGlobal('atof')
        atof_func = self.module.globals['atof']
        result = self.builder.call(atof_func, [receiver_result])
        return result

    def length_call(self, node, receiver_result):
        self.declareGlobal('strlen')
        strlen_func = self.module.globals['strlen']
        strlen_result = self.builder.call(strlen_func, [receiver_result])
        truncated_result = self.builder.trunc(strlen_result, ir.IntType(64))
        return truncated_result
