import click
import os
from tree_sitter import Language, Parser

import base64
import hashlib

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
@click.option("--writetoken", is_flag=True, help="Write the new file with the tokenized content")
@click.option("--writeast", is_flag=True, help="Write the new file with the AST content")
@click.option("--writerelativeast", is_flag=True, help="Write the AST content with relative positions")
@click.option("--writecompast", is_flag=True, help="Write the new file with the compressed AST content and hashing")
@click.option("--overwrite", is_flag=True, help="Overwrite the original .java file with the new content")
@click.option("-v", "--verbose", count=True, help="Increase output verbosity")
@click.argument("file_path", type=click.Path(exists=True))
## Formast 
def formast(file_path, writetoken, writeast, writerelativeast, writecompast, overwrite, verbose):

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
    
    ## Handling options 
    # Token based
    if writetoken:  
        tree = parse_java_file(parser, file_path)
        save_tokenized_file(file_path, tree)
    # AST based
    elif writeast:
        with open(file_path, "rb") as f:
            code = f.read()
        tree = parser.parse(code)
        ast_code = process_tree(tree, code)
        with open(file_path+".ast", 'w') as f:
            f.write(ast_code)
    # Compressed AST based
    elif writecompast:
        with open(file_path, "rb") as f:
            code = f.read()
        tree = parser.parse(code)
        ast_code = process_tree_comp(tree)
        with open(file_path+".ast", 'w') as f:
            f.write(ast_code)
    # Relative AST based
    elif writerelativeast:
        with open(file_path, "rb") as f:
            code = f.read()
        tree = parser.parse(code)
        ast_code = process_tree_relatively(tree, code)
        with open(file_path+".ast", 'w') as f:
            f.write(ast_code)


    # If overwrite is true, overwrite the original .java file with the .ast content
    if overwrite:
        with open(file_path+".ast", 'r') as ast_file:
            ast_content = ast_file.read()
        with open(file_path, 'w') as java_file:
            java_file.write(ast_content)
        os.remove(file_path+".ast")
        #log.info("Original .java file overwritten with .ast content!")
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

## Processes a tree, compressed AST with hashing
def process_tree_comp(tree):
    lookup = {}
    lines = []

    def process_node(node):
        line = ""

        if node.children:
            children = []
            for child in node.children:
                child_result = process_node(child)
                if child_result is not None:
                    children.append(child_result)
            line = 'B {} {}'.format(node.type, ' '.join(map(str, children)))
        else:
            text = node.text.decode('utf-8')
            line = 'L {}'.format(text)

        idx = lookup.get(line)
        if idx is not None:
            return idx

        hash_object = hashlib.sha256(line.encode('utf-8'))
        hash_value = int.from_bytes(hash_object.digest()[:8], byteorder='big', signed=True)
        idx = base64.urlsafe_b64encode(hash_value.to_bytes(8, byteorder='big', signed=True)).rstrip(b'=').decode('ascii')
        lines.append('{} {}'.format(idx, line))
        lookup[line] = idx

        return idx

    process_node(tree.root_node)
    return '\n'.join(lines)        


## Processes a tree and returns an AST 
def process_tree(tree, code):
    lines = []
    def process_node(node):
        if node.type == 'identifier':
            lines.append(f'N {code[node.start_byte:node.end_byte].decode("utf-8")}')
            lines.append(f'B identifier {len(lines) - 1}')
            return len(lines) - 1
        elif node.type == 'class':
            return None
        elif node.type == 'class_body':
            children = []
            for child in node.children:
                if child.type not in ['{', '}']:
                    child_index = process_node(child)
                    if child_index is not None:
                        children.append(child_index)
            lines.append(f'B {node.type} {" ".join(map(str, children))}')
            return len(lines) - 1
        else:
            children = []
            for child in node.children:
                child_index = process_node(child)
                if child_index is not None:
                    children.append(child_index)
            lines.append(f'B {node.type} {" ".join(map(str, children))}')
            return len(lines) - 1
    process_node(tree.root_node)
    return '\n'.join(lines)

## Processes the tree relatively
def process_tree_relatively(tree, code):
    lines = []
    def process_node(node):
        if node.type == 'identifier':
            lines.append(f'N {code[node.start_byte:node.end_byte].decode("utf-8")}')
            lines.append(f'B identifier -1')
            return len(lines) - 1
        elif node.type == 'class':
            return None
        elif node.type == 'class_body':
            children = []
            for child in node.children:
                if child.type not in ['{', '}']:
                    child_index = process_node(child)
                    if child_index is not None:
                        children.append(child_index)
            lines.append(f'B {node.type}')
            return len(lines) - 1
        else:
            children = []
            for child in node.children:
                child_index = process_node(child)
                if child_index is not None:
                    children.append(child_index)
            connections = [-len(lines) + i for i in children]
            lines.append(f'B {node.type} {" ".join(map(str, connections))}')
            return len(lines) - 1
    process_node(tree.root_node)
    return '\n'.join(lines)

## Parse the java file and return the tree
def parse_java_file(parser, file_path):
    if not is_java_file(file_path):
        raise ValueError('File must have a .java extension')
    
    with open(file_path, 'r') as f:
        src = f.read()

    tree_word = parser.parse(src.encode("utf8"))
    
    return tree_word 


## Save AST file
def save_ast_file(file_path, tree):
    with open(file_path, 'r') as f:
        src = f.read()
    with open(file_path+".ast", 'w') as f:
        f.write(process_tree(tree, src))

## Save tokenized file
def save_tokenized_file(file_path, tree):
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