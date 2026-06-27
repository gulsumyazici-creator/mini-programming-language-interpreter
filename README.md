# Mini Programming Language Interpreter

A Python interpreter for a small programming language designed for CmpE 260 Project 1.
The project includes a lexer, parser, AST structure, and evaluator with an explicit environment model.

## Features

* Integer and boolean values
* Arithmetic, comparison, and logical operators
* Variable declarations and assignments
* Conditional expressions
* First-class functions
* Recursion
* Closures
* Static lexical scoping by default
* Optional dynamic scoping with a command-line flag
* Print statements

## Bonus Features

* Strings with escape sequences and concatenation
* While loops
* Lists, indexing, `length`, and `append`
* Runtime type checking with error messages
* Higher-order function examples

## Project Structure

```text
.
├── interpreter.py
├── README.md
├── examples/
│   ├── basics.txt
│   ├── recursion.txt
│   ├── closures.txt
│   ├── scope.txt
│   └── higher_order.txt
└── docs/
    ├── grammar.txt
    ├── ast.txt
    └── report.pdf
```

## How to Run

Run a program with the default static scoping mode:

```bash
python interpreter.py examples/basics.txt
```

Run explicitly with static scoping:

```bash
python interpreter.py --scope static examples/scope.txt
```

Run with dynamic scoping:

```bash
python interpreter.py --scope dynamic examples/scope.txt
```

## Example Programs

The `examples` folder contains small programs demonstrating the main features:

* `basics.txt`: variables, arithmetic, comparisons, logic, assignment, and printing
* `recursion.txt`: recursive factorial function
* `closures.txt`: closure behavior with a counter function
* `scope.txt`: difference between static and dynamic scoping
* `higher_order.txt`: passing a function as an argument

## Notes

Only `print` statements produce standard output.
Syntax and runtime errors are printed to standard error, and the interpreter exits with a non-zero status code.
