# formast

An AST formatting tool to run on java files, with different formatting options. Available options are: 
    - tokenize
    - ast 
    - relative ast
    - sorted compressed ast


## Develop

Remember to download tree-sitter-java and run the following command (uncomment it in the __main__.py) to generate the language file, when you are running formastfor the first time.

```console
 Language.build_library(
     # Store the library in the `build` directory
     'build/my-languages.so',

     # Include one or more languages
     [
         '../../vendor/tree-sitter-java'
     ]
 )
```

To see the available options:
```console
pdm run formast --help
```

To run the executable:
```console
pdm run python -m formast <args>
```


