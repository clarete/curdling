import ast
import imp


class ImportVisitor(ast.NodeVisitor):

    def __init__(self):
        self.imports = []

    def visit_Import(self, node):
        self.imports.append(node.names[0].name)

    def visit_ImportFrom(self, node):
        self.imports.append(node.module)


def find_imported_modules(code):
    visitor = ImportVisitor()
    visitor.visit(ast.parse(code))
    return list(filter(None, visitor.imports))


def get_module_path(module_name):
    return imp.find_module(module_name)[1]
