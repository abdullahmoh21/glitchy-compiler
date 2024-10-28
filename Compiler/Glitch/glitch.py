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

# Initialize Rich console
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
        
class GlitchError(Exception):
    pass

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

    def run_game(self):
        self.main_menu()

    def display_banner(self):
        from pyfiglet import Figlet
        figlet = Figlet(font='slant')
        banner = figlet.renderText('Glitch Engine')
        console.print(Text(banner, style="bold magenta"))

    def main_menu(self):
        self.display_banner()
        menu = Table(show_header=False, box=box.ROUNDED)
        menu.add_column(justify="center")
        menu.add_row("1. Start Game")
        menu.add_row("2. Instructions")
        menu.add_row("3. Exit")
        console.print(Panel(menu, title="Main Menu", border_style="green"))
        
        choice = Prompt.ask("Select an option", choices=["1", "2", "3"], default="1")
        if choice == "1":
            self.run()
        elif choice == "2":
            self.show_instructions()
        elif choice == "3":
            console.print("[bold red]Goodbye![/bold red]")
            sys.exit(0)

    def show_instructions(self):
        instructions = Text()
        instructions.append("Welcome to the Glitch Engine!\n", style="bold underline blue")
        instructions.append("In each cycle, a random glitch will be applied to the code.\n")
        instructions.append("After the glitch, you'll be asked to identify which glitch occurred.\n")
        instructions.append("You can type '-1' to quit or 'hint' to get a hint.\n")
        console.print(Panel(instructions, title="Instructions", border_style="yellow"))
        Prompt.ask("Press Enter to return to the Main Menu")

    def run(self):
        console.print(Panel("[bold cyan]Welcome to the Glitch Engine![/bold cyan]", title="Glitch Game", border_style="blue"))
        while True:
            try:
                possible_glitches = self.possible_glitches()
                # Exclude glitches already used
                available_glitches = [glitch for glitch in possible_glitches if glitch not in self.used_glitches]
                
                if not available_glitches:
                    continue_game = Confirm.ask("All possible glitch types have been done. Do you want to continue?")
                    if continue_game:
                        self.used_glitches.clear()
                        available_glitches = possible_glitches.copy()
                        console.print("[green]Glitch pool has been reset.[/green]")
                    else:
                        console.print("[bold red]Exiting the Glitch Engine.[/bold red]")
                        break

                self.cycle(available_glitches)
                if self.glitch_applied and self.glitch_applied != GlitchType.NO_GLITCH:
                    self.used_glitches.add(self.glitch_applied)
                self.glitched_ast = copy.deepcopy(self.ast)  # Reset ast
                self.node_registry = self.glitched_ast.node_registry
            except Exception as e:
                console.print(f"[bold red]Glitch Engine failed: {e}[/bold red]")
                break

            continue_game = Confirm.ask("Do you want to continue to the next glitch intensity?")
            if not continue_game:
                console.print("[bold red]Exiting the Glitch Engine.[/bold red]")
                break

            self.cycle_count += 1

    def cycle(self, available_glitches):
        self.glitch_applied = None
        self.glitch_detail = None

        self.apply_glitches(available_glitches)
        console.print("[bold yellow]Output Console:[/bold yellow]")
        console.print("----------------------------------")
        self.compile_glitched()
        console.print("----------------------------------")

        self.present_mcq()

    def apply_glitches(self, available_glitches):
        """Applies a random glitch (or none) from the available glitches."""

        # 15% chance to have NO_GLITCH regardless of available glitches
        if random.random() <= 0.15:
            self.glitch_applied = GlitchType.NO_GLITCH
            self.glitch_detail = "No glitch occurred"
            self.glitch_history.append((self.glitch_applied, self.glitch_detail))
            return  # Exit early since no glitch is applied

        if not available_glitches:
            # If no available glitches and not applying NO_GLITCH, exit
            self.glitch_applied = GlitchType.NO_GLITCH
            self.glitch_detail = "No glitch occurred"
            self.glitch_history.append((self.glitch_applied, self.glitch_detail))
            console.print("[italic]No glitch occurred this cycle.[/italic]", style="dim")
            return

        glitch_to_apply = random.choice(available_glitches)
        
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
        question = Text("What glitch occurred? (Note: Not all glitches will have a visible effect on output!)\n", style="bold cyan")  # Header with no underline
        for idx, answer in enumerate(all_answers, 1):
            question.append(f"{idx}. {answer}\n", style="white")  # MCQs in plain white
        question.append("\nYour answer (-1 to quit, type 'hint' for a hint): ", style="bold yellow")

        # Display the question in a panel
        console.print(Panel(question, border_style="bright_blue"))

        while True:
            user_input = Prompt.ask("Your answer").strip().lower()

            if user_input == '-1':
                # Show correct answer if the user quits, using a distinct color (e.g., blue)
                correct_index = all_answers.index(correct_answer) + 1
                console.print(f"[bold blue]Correct Answer: {correct_index}[/bold blue]")
                sys.exit(0)
            elif user_input == 'hint':
                if random.random() <= 0.1:
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
                            console.print(f"[bold red]Incorrect.[/bold red] Correct Answer: {correct_index}")
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
            return f"The values of variable '{var1.name}' and '{var2.name}' have been shuffled"

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
        console.print("[bold blue]Initial AST:[/bold blue]")
        self.ast.print_content()
        console.print("[bold green]Glitched AST:[/bold green]")
        self.glitched_ast.print_content()
        
        # Initialize timers
        start_compile_time = None
        compile_duration = None
        llvm_compile_duration = None

        try:
            # Start timing for compilation from AST analysis to LLVM IR generation
            start_compile_time = time.time()

            analyzer = SemanticAnalyzer(self.glitched_ast)
            _, symbol_table = analyzer.analyze()

            if has_error_occurred():
                console.print("[bold red]Semantic analysis failed. Skipping compilation.[/bold red]")
                return

            # LLVM IR code generation phase
            llvmir_gen = LLVMCodeGenerator(symbol_table)
            llvm_ir = llvmir_gen.generate_code(self.glitched_ast)

            if has_error_occurred() or llvm_ir is None:
                console.print("[bold red]LLVM IR generation failed. Skipping compilation.[/bold red]")
                return

            # End timing for compilation and capture duration
            compile_duration = time.time() - start_compile_time

        except Exception as e:
            console.print(f"[bold red]Compilation failed during AST analysis or LLVM IR generation: {e}[/bold red]")
            return

        # Proceed if the compilation was successful
        if compile_duration:
            console.print(f"[cyan]Compilation Time (AST to LLVM IR): {compile_duration:.2f} seconds[/cyan]")

        # Start timing for LLVM IR to executable compilation
        llvm_compile_start_time = time.time()

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

                    # End timing for LLVM IR to executable compilation
                    llvm_compile_duration = time.time() - llvm_compile_start_time

                    # Print the duration for the LLVM IR to executable compilation
                    if llvm_compile_duration:
                        console.print(f"[cyan]Compilation Time (LLVM IR to Executable): {llvm_compile_duration:.2f} seconds[/cyan]")

                    # Remove the progress task after the compilation is complete
                    progress.remove_task(compile_task)

                # Step 4: Executing the compiled program with interactive input
                console.print("[green]Program executing...[/green]")  # Explicitly print status
                try:
                    with subprocess.Popen(
                        [executable_path],
                        stdin=sys.stdin,
                        stdout=sys.stdout,
                        stderr=sys.stderr
                    ) as process:
                        # Wait for the process to complete
                        process.wait()
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
        if hasattr(var1, 'cached_type'):
            del var1.cached_type
        if hasattr(var2, 'cached_type'):
            del var2.cached_type
        self.glitch_detail = f"Variables '{var1.name}' and '{var2.name}' were swapped"
    
    def ignore_function_calls(self):
        """Randomly ignores function calls, effectively removing them from the AST."""
        node = random.choice(self.node_registry['funcCall'])
        self.glitch_detail = f"Function call '{node.name}' at line {node.line} was ignored"
        node.replace_self(None)
    
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
        """Provides explanations for each glitch type."""
        explanations = {
            GlitchType.FLIP_LOG_OPS: "Logical operations have been inverted (e.g., '&&' to '||').",
            GlitchType.FLIP_COMPARISONS: "Comparison operators have been flipped (e.g., '==' to '!=').",
            GlitchType.VARIABLE_SHUFFLING: "Values of variables have been shuffled between each other.",
            GlitchType.IGNORE_FUNCTION_CALLS: "Function calls are being ignored and not executed.",
            GlitchType.FUNCTION_BODY_SWAP: "The bodies of two functions have been swapped.",
            GlitchType.ARITHMETIC_GLITCH: "Arithmetic operators have been randomly changed (e.g., '+' to '-').",
            GlitchType.CHANGE_VARIABLE: "A variable's value has been randomly altered.",
            GlitchType.REF_SWAP: "Variable references now point to different variables.",
            GlitchType.NO_GLITCH: "No glitch has occurred."
        }
        return explanations.get(glitch_type, "No explanation available.")
