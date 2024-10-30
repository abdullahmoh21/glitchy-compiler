import os
import unittest
import subprocess
from pathlib import Path

class TestCompile(unittest.TestCase):
    expected_outputs = {
        'ackermann.g': "7\n",
        'calculator.g': "148.571429\n",
        'cmplxExprs.g': "271.000000\n",
        'cmplxExprs2.g': "305.750000\n",
        'collatz.g': "111\n",
        'exp.g': "1047.000000\n",
        'fib.g': "93.000000\n",
        'gcd.g': "6\n",
        'isPrime.g': "true\n",
        'sum.g': "5.000000\n",
    }

    def run_compile(self, file_path):
        try:
            # Attempt to run the compile function with a timeout
            result = subprocess.run(
                ['python', '-m', 'Compiler.compile', file_path],  # Use -m to run as a module
                text=True,
                capture_output=True,
                check=True,
                timeout=5  # Set a 5-second timeout
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            print(f"TimeoutExpired: The file {file_path} took too long to compile.")
            return "Timeout"
        except subprocess.CalledProcessError as e:
            # Capture output if there was an error in the subprocess
            return e.stdout + e.stderr

def generate_test(file_path, expected_output):
    """
    Generates a test method for a given file and its expected output.
    """
    def test(self):
        actual_output = self.run_compile(file_path)
        
        # Normalize line endings
        actual_output = actual_output.replace('\r\n', '\n')
        expected = expected_output.replace('\r\n', '\n')

        self.assertEqual(actual_output, expected)
    
    return test


test_dir = Path(__file__).parent / 'testPrograms'
for file_path in test_dir.glob('*.g'):
    filename = file_path.name
    if filename in TestCompile.expected_outputs:
        expected_output = TestCompile.expected_outputs[filename]
        test_method = generate_test(file_path, expected_output)
        test_method_name = f'test_{filename.replace(".", "_")}'
        setattr(TestCompile, test_method_name, test_method)
    else:
        print(f"Warning: No expected output defined for {filename}")

if __name__ == '__main__':
    unittest.main()