import click
import os
from tree_sitter import Language, Parser

Language.build_library(
    # Store the library in the `build` directory
    'build/my-languages.so',

    # Include one or more languages
    [
        '../../vendor/tree-sitter-java'
    ]
)
JAVA_LANGUAGE = Language('build/my-languages.so', 'java')

parser = Parser()
parser.set_language(JAVA_LANGUAGE)


@click.command()
@click.option("--file", prompt="Path of the file", help="Path of the file")    
def cli(file):
    formast(file)
#@click.option("--file2", prompt="Path of the second file", help="Path of the second file")

## Formast 
def formast(file_path):
    tree = parse_java_file(file_path)  
    save_ast_file(file_path, tree)
    print("AST file saved!")

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
def parse_java_file(file_path):
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
    cli()
