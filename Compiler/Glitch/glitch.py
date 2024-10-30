from ctypes import CFUNCTYPE, c_void_p
import tempfile
import llvmlite.binding as llvm
from Compiler.Analyzer import *
from Compiler.Generator import *
from Compiler.utils import *
import llvmlite.ir as ir
from enum import Enum
import subprocess
import random
import time
import copy
import sys
import os

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich import box
console = Console()

class GlitchType(Enum):
    FLIP_LOG_OPS = "Flip Logical ops"
    FLIP_COMPARISONS = "Flip comparisons"
    VARIABLE_SHUFFLING = "Variable Shuffling"
    IGNORE_FUNCTION_CALLS = "Ignores Function Calls"
    FUNCTION_BODY_SWAP = "Function Body Swap"
    ARITHMETIC_GLITCH = "Random Arithmetic Glitch"
    CHANGE_VARIABLE = "Change A variable's value"
    REF_SWAP = "A variable reference could point to a different variable instead"
    NO_GLITCH = "No glitch occurred"
    # Not implemented:
    IF_COND = "Replaces an if statements condition to true or false. Making it always or never run"
    ARG_CHANGE = "Changes the value of an argument."

class GlitchEngine:
    def __init__(self, ast):
        self.ast = ast
        self.glitched_ast = copy.deepcopy(ast)
        self.node_registry = self.glitched_ast.node_registry
        self.cycle_count = 0
        self.glitch_applied = None
        self.glitch_detail = None
        self.glitch_history = []
        self.used_glitches = set()  # To track used glitches

        # LLVM Initialization
        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()

    def __del__(self):
        llvm.shutdown()

    def display_banner(self):
        from pyfiglet import Figlet
        figlet = Figlet(font='slant')
        banner = figlet.renderText('Glitchy')
        console.print(Text(banner, style="bold magenta"))

    def show_instructions(self):
        description = Text()
        description.append("Welcome to Glitchy!\n", style="bold blue")
        description.append("\n")
        description.append("• Experience the unexpected as random glitches alter your code.\n")
        description.append("• Identify the type of glitch that occurred after each cycle.\n")
        description.append("• Type '-1' at any time to quit the game.\n")
        description.append("• Use 'hint' to receive a clue when you're stuck.\n")
        console.print(Panel(description, title="Description", border_style="yellow"))
        Prompt.ask("Press Enter to start the game")

    def run(self):

        # self.display_banner()
        # self.show_instructions()

        while True:
            try:
                possible_glitches = self.possible_glitches()
                # Exclude glitches already used
                available_glitches = [glitch for glitch in possible_glitches if glitch not in self.used_glitches]

                if not available_glitches:
                    continue_game = Confirm.ask("All possible glitch types have run at least once. Do you want to continue?")
                    if continue_game:
                        self.used_glitches.clear()
                        available_glitches = possible_glitches.copy()
                    else:
                        console.print("[bold red]Exiting Glitchy.[/bold red]")
                        break

                self.cycle(available_glitches)
                if self.glitch_applied and self.glitch_applied != GlitchType.NO_GLITCH:
                    self.used_glitches.add(self.glitch_applied)
                self.glitched_ast = copy.deepcopy(self.ast)  # Reset ast and create new node_registry with correct refs
                self.node_registry = self.glitched_ast.node_registry
            except Exception as e:
                console.print(f"[bold red]Glitchy failed: {e}[/bold red]")
                break

            continue_game = Confirm.ask("Do you want to continue to the next glitch intensity?")
            if not continue_game:
                console.print("[bold red]Exiting Glitchy.[/bold red]")
                break

            self.cycle_count += 1

    def cycle(self, available_glitches):
        self.glitch_applied = None
        self.glitch_detail = None
        
        self.apply_glitches(available_glitches)
        self.compile_glitched()
        self.present_mcq()

    def apply_glitches(self, available_glitches):
        """Applies a random glitch (or none) from the available glitches."""

        # 15% chance to have NO_GLITCH regardless of available glitches
        if random.random() <= 0.15:
            self.glitch_applied = GlitchType.NO_GLITCH
            self.glitch_detail = "No glitch occurred"
            self.glitch_history.append((self.glitch_applied, self.glitch_detail))
            return  # Exit early since no glitch is applied

        # glitch_to_apply = random.choice(available_glitches)
        glitch_to_apply = GlitchType.FLIP_COMPARISONS

        # Apply the selected glitch
        if glitch_to_apply == GlitchType.FLIP_LOG_OPS:
            self.flip_logical_ops()

        elif glitch_to_apply == GlitchType.FLIP_COMPARISONS:
            self.flip_comparisons()

        elif glitch_to_apply == GlitchType.VARIABLE_SHUFFLING:
            self.variable_shuffling()

        elif glitch_to_apply == GlitchType.CHANGE_VARIABLE:
            self.change_variable()

        elif glitch_to_apply == GlitchType.IGNORE_FUNCTION_CALLS:
            self.ignore_function_calls()

        elif glitch_to_apply == GlitchType.FUNCTION_BODY_SWAP:
            self.function_body_swap()

        elif glitch_to_apply == GlitchType.ARITHMETIC_GLITCH:
            self.arithmetic_glitch()

        elif glitch_to_apply == GlitchType.REF_SWAP:
            self.ref_swap()

        self.glitch_applied = glitch_to_apply
        self.glitch_history.append((self.glitch_applied, self.glitch_detail))

    def present_mcq(self):
        correct_answer = self.glitch_detail
        all_answers = [correct_answer]
        incorrect_answers = self.generate_incorrect_answers(3, self.glitch_applied, self.glitch_detail)

        if incorrect_answers:
            all_answers.extend(incorrect_answers)
        else:
            console.print("[bold red]Unable to generate enough unique incorrect answers.[/bold red]")
            return

        random.shuffle(all_answers)

        # Create header and MCQ question in the panel
        question = Text("What glitch occurred? (Note: Not all glitches will have a visible effect on output!)\n", style="bold cyan")
        for idx, answer in enumerate(all_answers, 1):
            question.append(f"{idx}. {answer}\n", style="white")
        question.append("\nYour answer (-1 to quit, type 'hint' for a hint): ", style="bold yellow")

        # Display the question in a panel once
        console.print(Panel(question, border_style="bright_blue"))

        while True:
            user_input = Prompt.ask("").strip().lower()  # Empty prompt to align input after "Your answer: "

            if user_input == '-1':
                # Show correct answer if the user quits, using a distinct color (e.g., blue)
                correct_index = all_answers.index(correct_answer) + 1
                console.print(f"[bold blue]Correct Answer: ({correct_index}) {correct_answer}[/bold blue]")
                sys.exit(0)
            elif user_input == 'hint':
                if random.random() <= 0.15:
                    console.print("[italic]I am not helping you.[/italic]", style="dim")
                else:
                    explanation = self.get_glitch_explanation(self.glitch_applied)
                    console.print(f"[bold blue]Hint:[/bold blue] The glitch is of type: {explanation}")
                continue  # Ask for input again after providing hint
            else:
                try:
                    answer_index = int(user_input)
                    if 1 <= answer_index <= len(all_answers):
                        selected_answer = all_answers[answer_index - 1]
                        if selected_answer == correct_answer:
                            console.print("[bold green]Correct![/bold green]")
                        else:
                            # Show incorrect message with the correct answer index in white
                            correct_index = all_answers.index(correct_answer) + 1
                            console.print(f"[bold red]Incorrect.[/bold red] Correct Answer: ({correct_index}) {correct_answer}")
                        break  # Exit after answering
                    else:
                        console.print(f"[bold red]Invalid choice. Please select a number between 1 and {len(all_answers)}, '-1' to quit, or type 'hint'.[/bold red]")
                except ValueError:
                    console.print("[bold red]Invalid input. Please enter a number, '-1' to quit, or type 'hint'.[/bold red]")
                    
    def generate_incorrect_answers(self, length, actual_glitch_type, actual_glitch_detail):
        """
        Generates a list of plausible incorrect answers based on the possible glitches,
        avoiding the actual glitch detail.
        Ensures each is of a different type and not the actual glitch detail.
        """

        all_glitches = [glitch for glitch in GlitchType if glitch != actual_glitch_type and glitch != GlitchType.NO_GLITCH]
        random.shuffle(all_glitches)
        incorrect_answers = []

        for glitch in all_glitches:
            answer = self._generate_answer_by_type(glitch)
            if answer and answer != actual_glitch_detail and answer not in incorrect_answers:
                incorrect_answers.append(answer)
                if len(incorrect_answers) == length:
                    break

        # If not enough incorrect answers, add generic ones
        while len(incorrect_answers) < length:
            random_glitch = random.choice(all_glitches)
            incorrect_answers.append(f"A random glitch of type '{random_glitch.value}' occurred.")

        return incorrect_answers

    def _generate_answer_by_type(self, selected_type):
        """Generates an incorrect answer based on the specified type."""

        if selected_type == GlitchType.CHANGE_VARIABLE and self.node_registry.get('varDecl'):
            var = random.choice(self.node_registry['varDecl'])
            var_type = var.evaluateType()

            if var_type == 'integer':
                int_val = random.randint(0, 100)
                incorrect_value = int_val
            elif var_type == 'double':
                double_val = round(random.uniform(0, 100), 2)
                incorrect_value = double_val
            elif var_type == 'string':
                str_val = random.choice([
                    "Why is glitchy so good?", "Who made this genius language?",
                    "Please end me.", "I am so happy!", "I had to add a Hello World!!",
                    "Does heaven exist?", "I am so bored", "Can I be loved?",
                    "I can make a compiler, but can I make a life for myself?"
                ])
                incorrect_value = f'"{str_val}"'
            elif var_type == 'boolean':
                # Assuming var.value is a Boolean instance with a 'value' attribute
                incorrect_value = "true" if var.value.value == False else "false"
            else:
                incorrect_value = "Null"
            return f"Variable '{var.name}'s value changed to {incorrect_value}"

        elif selected_type == GlitchType.IGNORE_FUNCTION_CALLS and self.node_registry.get('funcCall'):
            func = random.choice(self.node_registry['funcCall'])
            return f"Function call '{func.name}' at line {func.line} was ignored"

        elif selected_type == GlitchType.ARITHMETIC_GLITCH and self.node_registry.get('binOp'):
            node = random.choice(self.node_registry['binOp'])
            ops = ['+', '-', '*', '/']
            if hasattr(node, 'operator') and node.operator in ops:
                ops.remove(node.operator)
            new_operator = random.choice(ops) if ops else node.operator
            return f"Arithmetic operator at line {node.line} changed from '{node.operator}' to '{new_operator}'"

        elif selected_type == GlitchType.FUNCTION_BODY_SWAP and len(self.node_registry.get('funcDecl', [])) > 1:
            func1, func2 = random.sample(self.node_registry['funcDecl'], 2)
            return f"Function bodies of '{func1.name}' and '{func2.name}' were swapped"

        elif selected_type == GlitchType.FLIP_LOG_OPS and self.node_registry.get('logOp'):
            node = random.choice(self.node_registry['logOp'])
            flip_map = {'&&': '||', '||': '&&'}
            original_op = node.operator
            flipped_op = flip_map.get(original_op, original_op)
            return f"Logical operator at line {node.line} flipped from '{original_op}' to '{flipped_op}'"

        elif selected_type == GlitchType.FLIP_COMPARISONS and self.node_registry.get('comparison'):
            node = random.choice(self.node_registry['comparison'])
            flip_map = {'==': '!=', '!=': '==', '>': '<=', '<': '>=', '>=': '<', '<=': '>'}
            original_op = node.operator
            flipped_op = flip_map.get(original_op, original_op)
            return f"Comparison operator at line {node.line} flipped from '{original_op}' to '{flipped_op}'"

        elif selected_type == GlitchType.VARIABLE_SHUFFLING and len(self.node_registry.get('varDecl', [])) > 1:
            var1, var2 = random.sample(self.node_registry['varDecl'], 2)
            return f"The values of variable '{var1.name}'(line {var1.line}) and '{var2.name}(line {var2.line})' have been shuffled"

        elif selected_type == GlitchType.REF_SWAP and len(self.node_registry.get('varRef', [])) > 1:
            var1, var2 = random.sample(self.node_registry['varRef'], 2)
            while var1.name == var2.name:
                var2 = random.choice(self.node_registry['varRef'])
            return f"The reference of '{var1.name}' on line {var1.line} points to the variable '{var2.name}' instead"

        elif selected_type == GlitchType.NO_GLITCH:
            return "No glitch occurred"

        return None

    def possible_glitches(self):
        """Returns a list of possible glitches based on AST statistics."""
        glitches = []

        if self.node_registry.get('comparison'):
            glitches.append(GlitchType.FLIP_COMPARISONS)

        if self.node_registry.get('logOp'):
            glitches.append(GlitchType.FLIP_LOG_OPS)

        if len(self.node_registry.get('varDecl', [])) > 1:
            glitches.append(GlitchType.VARIABLE_SHUFFLING)

        if self.node_registry.get('funcCall'):
            glitches.append(GlitchType.IGNORE_FUNCTION_CALLS)

        if len(self.node_registry.get('funcDecl', [])) > 1:
            glitches.append(GlitchType.FUNCTION_BODY_SWAP)

        if self.node_registry.get('binOp'):
            glitches.append(GlitchType.ARITHMETIC_GLITCH)

        if self.node_registry.get('varDecl'):
            glitches.append(GlitchType.CHANGE_VARIABLE)

        if len(self.node_registry.get('varRef', [])) > 1:
            glitches.append(GlitchType.REF_SWAP)

        return glitches

    def compile_glitched(self):
        clear_errors()      # Clear errors raised by previous cycles
        # Initialize timers
        start_compile_time = None
        compile_duration = None

        try:
            start_compile_time = time.time()
            analyzer = SemanticAnalyzer(self.glitched_ast)
            _, symbol_table = analyzer.analyze()

            if has_error_occurred():
                return  

            # LLVM IR code generation phase
            llvmir_gen = LLVMCodeGenerator(symbol_table)
            llvm_ir = llvmir_gen.generate_code(self.glitched_ast)

            if has_error_occurred() or llvm_ir is None:
                console.print("[bold red]LLVM IR generation failed. Skipping compilation.[/bold red]")
                return
        except Exception as e:
            console.print(f"[bold red]Compilation failed during AST analysis or LLVM IR generation: {e}[/bold red]")
            return

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                object_path = os.path.join(temp_dir, "output.o")
                executable_path = os.path.join(temp_dir, "a.out")

                # Unified Progress Spinner for compilation tasks
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    compile_task = progress.add_task("[magenta]Compiling to Executable...", total=None)

                    try:
                        # Step 1: Parse and verify LLVM IR
                        mod = llvm.parse_assembly(str(llvm_ir))
                        mod.verify()

                        # Step 2: Emit object code
                        target_machine = llvm.Target.from_default_triple().create_target_machine()
                        with open(object_path, 'wb') as obj_file:
                            object_code = target_machine.emit_object(mod)
                            if not object_code:
                                raise GlitchError("Failed to emit object code.")
                            obj_file.write(object_code)

                        # Step 3: Link executable
                        result = subprocess.run(['clang', object_path, '-o', executable_path], capture_output=True, text=True)
                        if result.returncode != 0:
                            console.print(f"[bold red]Linking failed: {result.stderr}[/bold red]")
                            return

                    except Exception as e:
                        console.print(f"[bold red]Compilation to executable failed: {e}[/bold red]")
                        return
                    finally:
                        # Ensure stdin is flushed and any remaining input is cleared
                        try:
                            sys.stdin.flush()
                        except Exception:
                            pass  # Not all stdin objects can be flushed, so we can ignore this in case of an error.

                    compile_duration = time.time() - start_compile_time

                    if compile_duration:
                        console.print(f"[cyan]Compilation Time: {compile_duration:.2f} seconds[/cyan]")
                    progress.remove_task(compile_task)

                console.print("[green]Program executing...[/green]")  # Explicitly print status
                console.print("[bold yellow]Output Console:[/bold yellow]")
                console.print("----------------------------------")
                try:
                    with subprocess.Popen(
                        [executable_path],
                        stdin=sys.stdin,
                        stdout=sys.stdout,
                        stderr=sys.stderr
                    ) as process:
                        # Wait for the process to complete
                        process.wait()
                        console.print("----------------------------------")
                        console.print("[green]Execution finished.[/green]")

                except Exception as e:
                    console.print(f"[bold red]Execution failed: {e}[/bold red]")

        except subprocess.CalledProcessError as cpe:
            console.print(f"[bold red]Linking failed: {cpe}[/bold red]")
        except FileNotFoundError as fnfe:
            console.print(f"[bold red]Required tool not found: {fnfe}[/bold red]")
            console.print("Please ensure that 'clang' is installed and in your system's PATH.")
        except GlitchError as ge:
            console.print(f"[bold red]{ge}[/bold red]")
        except Exception as e:
            raise GlitchError(f"{e}")

    # ------------------------------- Glitch Helpers ------------------------------- #

    def flip_logical_ops(self):
        """Applies '!' to randomly chosen logical operation node."""
        node = random.choice(self.node_registry['logOp'])
        new_node = UnaryOp('!', node, line=node.line)
        node.replace_self(new_node)
        self.glitch_detail = f"Logical operation at line {node.line} flipped with '!' operator"

    def flip_comparisons(self):
        """Flips the operator of a randomly chosen comparison node."""
        node = random.choice(self.node_registry['comparison'])
        # Map of comparison operators to their flipped counterparts
        flip_map = {
            '==': '!=',
            '!=': '==',
            '<': '>=',
            '>': '<=',
            '<=': '>',
            '>=': '<'
        }

        # Get the new flipped operator
        flipped_operator = flip_map.get(node.operator, node.operator)
        new_node = Comparison(node.left, flipped_operator, node.right, line=node.line)
        node.replace_self(new_node)
        self.glitch_detail = f"Comparison at line {node.line} flipped from '{node.operator}' to '{flipped_operator}'"

    def variable_shuffling(self):
        """Randomly swaps the values of two variables in the current scope and deletes their cached_type."""
        var1, var2 = random.sample(self.node_registry['varDecl'], 2)
        var1.value, var2.value = var2.value, var1.value
        self.glitch_detail = f"The values of variables '{var1.name}'(line: {var1.line}) and '{var2.name}'(line: {var2.line}) were swapped"

    def ignore_function_calls(self):
        """Randomly ignores function calls, effectively removing them from the AST."""
        node = random.choice(self.node_registry['funcCall'])
        node.replace_self(None)
        self.glitch_detail = f"Function call '{node.name}' at line {node.line} was ignored"

    def function_body_swap(self):
        """Swaps the function body of two functions."""
        func1, func2 = random.sample(self.node_registry['funcDecl'], 2)
        func1.body, func2.body = func2.body, func1.body
        self.glitch_detail = f"Function bodies of '{func1.name}' and '{func2.name}' were swapped"

    def arithmetic_glitch(self):
        """Swaps arithmetic operators in a random binary operation node."""
        node = random.choice(self.node_registry['binOp'])
        operators = ['+', '-', '*', '/']
        if hasattr(node, 'operator') and node.operator in operators:
            operators.remove(node.operator)     # Remove the current operator from the list
        swapped_operator = random.choice(operators) if operators else node.operator
        new_node = BinaryOp(node.left, swapped_operator, node.right, line=node.line)
        node.replace_self(new_node)
        self.glitch_detail = f"Arithmetic operator at line {node.line} changed from '{node.operator}' to '{swapped_operator}'"

    def ref_swap(self):
        var1, var2 = random.sample(self.node_registry['varRef'], 2)
        while var1.name == var2.name:
            var2 = random.choice(self.node_registry['varRef'])
        new_ref = VariableReference(var2.name, line=var1.line)
        var1.replace_self(new_ref)
        var1.value = None
        var1.type = None
        var1.scope = None
        self.glitch_detail = f"The variable reference '{var1.name}' on line {var1.line} now points to the variable '{var2.name}'"

    def change_variable(self):
        """Changes the value of a variable to a random value of the same type."""
        var = random.choice(self.node_registry['varDecl'])
        var_ty = var.evaluateType()
        old_value = var.value
        if var_ty in ["string"]:
            str_val = random.choice([
                "Who made this phenomenal language?", "Please end me.", "I am so happy!",
                "I had to add a Hello World!!", "Does heaven exist?", "I am so bored",
                "Can I be loved?", "I can make a compiler, but can I make a life for myself?",
                "Who will compile my soul?"
            ])
            new_value = String(str_val)
        elif var_ty in ["integer"]:
            int_val = random.randint(0, 100)
            new_value = Integer(int_val)
        elif var_ty in ["double"]:
            double_val = round(random.uniform(0, 100), 2)
            new_value = Double(double_val)
        elif var_ty in ["boolean"]:
            new_value = Boolean(not old_value.value if isinstance(old_value, Boolean) else True)
        else:
            new_value = Null()

        var.value = new_value

        if hasattr(var, 'cached_type'):
            var.cached_type = None
        self.glitch_detail = (
            f"Variable '{var.name}'s value on line {var.line} changed from {str(old_value)} to {str(var.value)}"
        )

    def get_glitch_explanation(self, glitch_type):
        """Provides vague hints for each glitch type."""
        hints = {
            GlitchType.FLIP_LOG_OPS: "Something about how the program makes decisions might feel different.",
            GlitchType.FLIP_COMPARISONS: "The way values are being compared has been subtly altered.",
            GlitchType.VARIABLE_SHUFFLING: "Some data might not be where you expect it to be.",
            GlitchType.IGNORE_FUNCTION_CALLS: "Certain actions that should happen might not be occurring.",
            GlitchType.FUNCTION_BODY_SWAP: "The internal behavior of some parts of the code has changed unexpectedly.",
            GlitchType.ARITHMETIC_GLITCH: "Basic calculations seem a bit off.",
            GlitchType.CHANGE_VARIABLE: "A key piece of data has been unexpectedly modified.",
            GlitchType.REF_SWAP: "References in the code might be pointing to different sources now.",
            GlitchType.NO_GLITCH: "No hints... It's too easy :)"
        }
        return hints.get(glitch_type, "No hint available.")