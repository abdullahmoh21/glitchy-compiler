# Glitchy Language Compiler

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Glitches](#glitches)
- [Installation](#installation)
- [Usage](#usage)
- [Examples](#examples)
- [Todo](#todo)
- [Contributing](#contributing)
- [Testing](#testing)
- [License](#license)

## Overview

Glitchy is an educational programming language designed to blend features from my favorite languages into an engaging platform for learning both programming and compiler design. Built with a Python-based multi-stage compiler that generates LLVM Intermediate Representation (IR), Glitchy leverages LLVM’s Just-In-Time (JIT) execution to provide real-time performance and high-efficiency code execution.

The goal with Glitchy is to demystify compilers, removing the sense of "black magic" often associated with them. Users are encouraged not just to write code but to also gain insights into what happens behind the scenes during compilation. This is achieved through detailed optional logs that show each step of the compilation process. Users are also encouraged to explore the compiler code itself!

One of the unique aspects of Glitchy is the incorporation of random "glitches," turning coding into an interactive challenge where users must troubleshoot unexpected behavior and learn through dynamic multiple-choice questions (MCQs).

The language features type inference, optional annotations, and a quirky type-checking system. For instance, Glitchy supports variable type strings, so `int`, `inte`, `integ`, and `integer` are all valid integer types. With Glitchy, you'll not only debug your code but also the compiler : )

## Features

- **Basic Constructs**: Includes `if`, `elif`, `else`, `for`, `while` loops, and functions (see [samples](samples)).

- **Type Inference**: Automatically infers the data type of variables without requiring explicit type declarations.

  ```glitchy
  set num = 10          // num is inferred as integer
  set name = "Glitchy"  // name is inferred as string
  ```

- **Optional Type Annotations**: Users can provide type annotations, which the compiler enforces.

  ```glitchy
  set num:int = 10
  set name:string = "Glitchy"
  ```

- **Flexible Type Names**: Allows various acceptable type names for the same underlying type. All these examples are valid:

  ```glitchy
  set num:int = 10
  set num:integ = 10
  set num:integer = 10
  ```

  ```glitchy
  set name:str = "Hello"
  set name:string = "World"
  ```

- **Flexible Type Comparison**: When checking the type of data using the `typeof(some_value)` function, which returns a string like `"boolean"`, Glitchy allows flexibility in type comparison. The compiler automatically normalizes type names during comparisons, enabling the following:

  ```glitchy
    set x = true
    typeof(x) == "bool"         // true
    typeof(x) == "boolean"      // true
  ```

  However, normal string comparisons remain unchanged:

  ```glitchy
    "str" == "string" // false
  ```

## Glitches

The Glitch feature introduces controlled unexpected behavior in the program whenever the function `glitch()` is called. This function triggers a game that tests users on their ability to debug and troubleshoot code. When this function is **explicitly** called, the program introduces a controlled glitch and runs the "glitched" code instead.

After execution, users are shown the output or error generated and are asked through multiple-choice questions (MCQs) to determine what happened. This encourages deeper understanding and problem-solving skills. Possible glitches include:

- **Logical Operation Inversion:** Logical operators like && (and) could be inverted to || (or)
- **Comparison Operator Flipping:** Comparison operators could be flipped (e.g., == to !=)
- **Ignored Function Calls:** Certain function calls might be ignored and not executed.
- **Function Body Swapping:** The bodies of two functions could be swapped.
- **Arithmetic Operator Change:** An arithmetic operator could be randomly changed (e.g., `+` to `*`).
- **Variable Swapping:** The values of two variables could be swapped.
- **Random Variable Alteration:** A variable's value could be randomly altered.
- **Variable Reference Redirection:** Variable references could point to different variables.
- **No Glitch:** Sometimes, no glitches are introduced to test your confidence in your own code

This feature turns coding into an interactive learning experience, helping users to understand not just the code they write but also how unexpected changes can affect program behavior.

## Installation

To install the Glitchy compiler, ensure you have Python, `pip`, and `Clang` installed on your system.

1. **Install Python and `pip`**:

- You can download Python (which includes `pip`) from [here](https://www.python.org/downloads/).

2. **Install Clang**:

- Make sure Clang is installed and accessible in your system's PATH.
  - **Ubuntu**: `sudo apt-get install clang`
  - **macOS**: `brew install llvm`
  - **Windows**: Download from [LLVM's website](https://llvm.org/) and ensure Clang is added to your PATH.

3. **Clone the repository** and navigate to the project directory:

```bash
git clone https://github.com/abdullahmoh21/glitchy-compiler.git
cd glitchy-compiler
```

4. Install Glitchy and its dependencies using pip:

```bash
pip install .
```

## Usage

After installation, you can run Glitchy files using the following command:

```bash
glitchy example/file.g --log [level]
```

_Log levels can be optionally set from 1 to 3 using the log flag_

## Examples

- **Ackermann Function**:

```glitchy
// Highly recursive Ackermann function
function int ackermann(m:int, n:integer) {
    print("Ackermann called!")
    if (m == 0) {
        return n + 1
    } elif (m > 0 && n == 0) {
        return ackermann(m - 1, 1)
    } else {
        return ackermann(m - 1, ackermann(m, n - 1))
    }
}
    }
}

set m = input().toInteger()
set n = input().toInteger()
print("Ackermann(" + m + ", " + n + ") = " + ackermann(m, n))
```

- **Collatz Conjecture**:

```glitchy
function void collatz(n:int) {
    print("Starting number: " + n)
    set steps = 0

    while (n != 1) {
        if (n % 2 == 0) {
            n = n / 2
        } else {
            n = n * 3 + 1
        }
        print("Next number: " + n)
        steps++
    }
    print("Collatz Conjecture completed in " + steps + " steps.")
}

set num = input().toInteger()
collatz(num)
```

## Todo

- Arrays
- More glitches
- More builtin functions

## Contributing

This is a solo project and as such, I have 100% missed something. If you find any issues or want to expand on the project, feel free to open issues or submit pull requests on the GitHub repository.

## Testing

Glitchy uses the unittest framework for testing. You can run the tests using the following command:

```bash
python -m unittest discover
```

## License

This project is licensed under the [MIT License](LICENSE.md.md).
