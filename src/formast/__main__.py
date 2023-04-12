import click
import os
from tree_sitter import Language, Parser

import logging

from pathlib import Path

log = logging.getLogger(__name__)

# Language.build_library(
#     # Store the library in the `build` directory
#     'build/my-languages.so',

#     # Include one or more languages
#     [
#         '../../vendor/tree-sitter-java'
#     ]
# )
language_file = Path(__file__).absolute().parent.parent.parent / 'build' / 'my-languages.so'
JAVA_LANGUAGE = Language(str(language_file), 'java')

@click.command()
@click.option("--overwrite", is_flag=True, help="Overwrite the original .java file with the .ast content")
@click.option("-v", "--verbose", count=True, help="Increase output verbosity")
@click.argument("file_path", type=click.Path(exists=True))
## Formast 
def formast(file_path, overwrite, verbose):

    # initialize logging
    logging.basicConfig(level=verbose)

    log.info("Formast v0.1.0")

    # Load the language (assuming the language is created, if not run the commented code above)
    language_file = Path(__file__).absolute().parent.parent.parent / 'build' / 'my-languages.so'
    log.debug("Using language file: %s", language_file)
    JAVA_LANGUAGE = Language(str(language_file), 'java')
    parser = Parser()
    parser.set_language(JAVA_LANGUAGE)
    log.info("Sucessfully created parser.")

    log.info(f"Processing {file_path}...")
    tree = parse_java_file(parser, file_path)  
    save_ast_file(file_path, tree)

    # If overwrite is true, overwrite the original .java file with the .ast content
    if overwrite:
        with open(file_path+".ast", 'r') as ast_file:
            ast_content = ast_file.read()
        with open(file_path, 'w') as java_file:
            java_file.write(ast_content)
        os.remove(file_path+".ast")
        log.info("Original .java file overwritten with .ast content!")
    else:
        log.info("AST file saved!")


## Tree traversal function
def traverse(tree):
    cursor = tree.walk()
    descend = [True]

    while True:
        if descend[-1]:
            yield cursor.node
        if descend[-1] and cursor.goto_first_child():
            descend[-1] = False
            descend.append(True)
        elif cursor.goto_next_sibling():
            descend[-1] = True
        elif cursor.goto_parent():
            descend.pop()
        else:
            break

## Parse the java file and return the tree
def parse_java_file(parser, file_path):
    if not is_java_file(file_path):
        raise ValueError('File must have a .java extension')
    
    with open(file_path, 'r') as f:
        src = f.read()

    tree_word = parser.parse(src.encode("utf8"))
    
    return tree_word 

## Save the ast file
def save_ast_file(file_path, tree):
    with open(file_path+".ast", 'w') as f:
        for node in traverse(tree):
            if node.child_count == 0:
                f.write(node.text.decode("utf8"))
                f.write("\n")

## Check if the file is a java file
def is_java_file(file_path):
    return os.path.splitext(file_path)[1] == '.java'

if __name__ == "__main__":
    formast()