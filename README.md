# Genrodin

## Description

Simple script to generate easily the structure of a program proof with Rodin (Event-B).

## Dependencies

Genrodin uses Python 3 and the `lxml` external library. This library could be installed with the following command on Linux :
```
$ pip3 install lxml
```
and the following one on Windows :
```
C:\> python -m pip install lxml
```

## Usage

Let say you have the following C function and you want to write a proof for it using Rodin:
```c
void process(unsigned int n) {
    int z, int i;
    z = 3;
    for (i = 0; i < n; i++) {
        if (z < 13) {
            z += 2 * i;
        } else {
            z += i;
        }
    }
    return z;
}
```

There is the same code rewritten for a program proof:
```
constants n
variables z, i

// l0 : ...
z := 3
// l1 : ...
i := 0
// l2 : ...
while (i < n) {
    // l3 : ...
    if (z < 13) {
        // l4 : ...
        z := z + 2 * i
        // l5 : ...
    } else {
        // l6 : ...
        z := z + i
        // l7 : ...
    }
    // l8 : ...
    i := i + 1
    // l9 : ...
}
// l10 : ...
```

Each line `// l$x : ...` represents an annotation added to the code for the proof. The predicate written for `l0` represents the precondition, and the predicate written for `l10` represents the post-condition (typically).

To make a program proof with Rodin, you need to do a lot of boring stuff:
+ create a constant `l$x` for each annotation
+ create a set `Lines`, and tell Rodin that this set is composed of all `lx` elements
+ create a variable `pc` representing the program cursor
+ create an invariant `Pl$x` for each annotation of the form `pc = l$x => (...)`, which will check that at each point of the program, the annotation is verified
+ create a bunch of events, representing the program flow. Theses events are divided in two categories :
    - flow events, which represents a move of the program cursor (`pc`) -- no variables are modified during those events. In our example, they are `l2 -> l3`, `l2 -> l10`, `l3 -> l4`, `l3 -> l6`, `l5 -> l8`, `l7 -> l8`, `l9 -> l3` and `l9 -> l10`. They can be fully determined and written just by knowing the structure of the program and the conditions of the if/loop constructs.
    - action events, where the actual variable affectations take place. In our example, they are `l0 -> l1`, `l1 -> l2`, `l4 -> l5`, `l6 -> l7` and `l8 -> l9`.

The `genrodin.py` script will take a program structure description file as an input, with the following format:
```
last_annotation_nb
construct_1
construct_2
construct_3
...
construct_n
```

+ `last_annotation_nb` is the last number used for our annotations, which is also the total number of concrete lines of our program. In the example, it's `10`
+ `construct_$x` tells Genrodin that the program have a `if`/`while` construct at a specific position. Supported formats are:
    - `while:cond:annotation_nb_before:annotation_nb_after`, where
        * `cond` is the condition of the `while` loop, which can include any Rodin-supported mathematical characters
        * `annotation_nb_before` is the annotation number preceding the `while` construct. In our example, it's `2`
        * `annotation_nb_after` is the annotation number following the end brace of the `while` construct. In our example, it's `10`
    - `if:cond:annotation_nb_before_if:annotation_nb_before_else:annotation_b_after`
        * is the condition of the `if` construct, which can include any Rodin-supported mathematical characters
        * `annotation_nb_before_if` is the annotation number preceding the `if` keyword. In our example, it's `3`
        * `annotation_nb_before_else` is the annotation number preceding the `else` keyword. In our example, it's `5`
        * `annotation_nb_after` is the annotation number after the whole `if/else` construct. In our example, it's `8`

The full program structure definition file (`example.desc`) for our example program is:
```
10
while:i < n:2:10
if:z < 13:3:5:8
```

Genrodin will process this description, and generate:
+ the constants `l$x` and the associated set `Lines` in a Rodin context file
+ a Rodin machine file, which sees the generated context, and composed of
    - a variable `pc`, and the type invariant `pc : Lines`
    - an invariant per annotation, of the form `pc = l$x => (⊤)`, which must be filled by the user
    - an initialisation event, which sets `pc := 0`
    - all the required flow events (events with the comment `// FLOW`), where `pc` is handled. There is nothing to add manually to these events!
    - all the required action events (events with the comment `// TBD`). The logic to handle the program cursor is already generated, you just need to add the real action/affectation that happens at this position.

The second (mandatory) argument of the Genrodin script is the name radical for the generated files. If the given radical is `example`, files named `example_context.buc` and `example_machine.bum` will be generated.

After the generation of the context and machine files, you can create a project on Rodin with the same name as the chosen radical, put those files in the associated folder, and on the project root in Rodin: *Right click > Refresh*.

There's how you can generate the context and machine files for the example program (these files are also available in this Git repo):
```
$ python3 genrodin.py example.desc example
Generation done!
```
Here's what it looks like on Rodin.

The context:
![Context file preview](https://raw.githubusercontent.com/tbagrel1/genrodin/master/screenshots/context.png)

The first part of the machine (with some flow events):
![Machine file preview 1](https://raw.githubusercontent.com/tbagrel1/genrodin/master/screenshots/machine1.png)

Some action events of the machine:
![Machine file preview 2](https://raw.githubusercontent.com/tbagrel1/genrodin/master/screenshots/machine2.png)

## Remarks

+ Be careful! Braces on `if` conditions and `while` loops in the rewritten program should be placed exactly like in the example (to enable Genrodin to distinguish action lines and flow lines) :
    - for a `while` loop:
        - the opening brace must be on the same line as the `while` keyword
        - the closing brace must be on a separate line at the end
    + for a `if/else` construct:
        + the opening brace following the `if` keyword must be on the same line as the keyword
        + the closing brace before the `else` keyword and the opening brace following the `else` keyword must be on the same line as the keyword (result: `} else {` on a single line)
        + the closing brace which ends the construct must be on a separate line at the end
        + each `if/else` construct must have an else clause. If the else clause is empty, this is what you should have:
```
if (cond) {
    action
} else {
}
```
+ Rodin can detect errors in the generated events. Most of the time, it is enough to open (unfold) the events in the GUI to allow Rodin to transform the ASCII characters into mathematical one, and the errors should magically disappear with a *Ctrl + S*.

## Author and contributions

My name is Thomas BAGREL, and I'm currently a 2nd year student of TELECOM Nancy Engineer School and apprentice at TRACIP SAS. This script was written for MVSI courses at TELECOM Nancy (taught by Dominique MERY), which involve a lot of Rodin program proofs.

I would be glad to receive any critic or suggestion to improve this program!