import ast
import astor
import importlib.util
import builtins
from dataclasses import dataclass
from typing import List, Set


@dataclass
class SpecificImport:
    name: str
    alias: str | None


@dataclass
class ImportSignature:
    name: str
    alias: str | None
    specified: List[SpecificImport]


@dataclass
class FunctionSignature:
    name: str
    args: List[str]
    return_type: str | None
    source_code: str
    dependencies: Set[str]

    def __repr__(self) -> str:
        return (
            f"FunctionSignature(name={self.name!r}, args={self.args!r}, return_type={self.return_type!r},"
            f" source_code=..., dependencies={self.dependencies!r})"
        )


@dataclass
class ClassSignature:
    name: str
    args: List[str]
    methods: List[FunctionSignature]


@dataclass
class ModuleSignature:
    imports: List[ImportSignature]
    functions: List[FunctionSignature]
    classes: List[ClassSignature]


class PySignature:
    def __init__(self, file_path: str | None, code: str | None = None):
        self.file_path = file_path
        if file_path is not None:
            self.signature = self.analyze_file()
        elif code is not None:
            self.signature = self.extract_code_info(code)
        self.name = self.extract_script_name()
        self.module_name = self.extract_script_module_name()

    def extract_script_name(self) -> str | None:
        if self.file_path is not None:
            return self.file_path.split("/")[-1].split(".")[0]

    def extract_script_module_name(self) -> str | None:
        if self.file_path is not None:
            path = self.file_path.split("/")
            if len(path) > 2:
                return path[-2]

    def extract_imports(self, node: ast.Module) -> List[ImportSignature]:
        imports = []
        for item in node.body:
            if isinstance(item, (ast.Import, ast.ImportFrom)):
                if isinstance(item, ast.Import):
                    for alias in item.names:
                        imports.append(ImportSignature(name=alias.name, alias=alias.asname, specified=[]))
                else:
                    specified = [SpecificImport(name=alias.name, alias=alias.asname) for alias in item.names]
                    if item.module is not None:
                        imports.append(ImportSignature(name=item.module, alias=None, specified=specified))
        return imports

    def is_std_lib(self, module_name: str) -> bool:
        print("\n\nMODULE NAME:", module_name, "\n\n")
        if module_name in dir(builtins):
            print("BUILTINS")
            return True
        return False

    def find_dependencies(self, node: ast.AST) -> Set[str]:
        dependencies = set()
        local_vars = set()
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.Name):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or child.id not in {
                    arg.arg for arg in node.args.args
                }:
                    dependencies.add(child.id)
            elif isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        local_vars.add(target.id)
            elif isinstance(node, ast.With):
                for item in node.items:
                    if isinstance(item, ast.withitem):
                        if isinstance(item.context_expr, ast.Name):
                            dependencies.discard(item.context_expr.id)
            dependencies |= self.find_dependencies(child)
        dependencies -= local_vars
        return dependencies

    def extract_function_info(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionSignature:
        func_name = node.name
        args = [arg.arg for arg in node.args.args]
        return_type = ast.unparse(node.returns) if node.returns else None
        source_code = astor.to_source(node).strip()
        dependencies = self.find_dependencies(node) - {arg.arg for arg in node.args.args} - {func_name}
        dependencies -= {dep for dep in dependencies if self.is_std_lib(dep)}
        return FunctionSignature(func_name, args, return_type, source_code, dependencies)

    def extract_class_info(self, node: ast.ClassDef) -> ClassSignature:
        class_name = node.name
        methods = []
        init_args = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_info = self.extract_function_info(item)
                methods.append(method_info)
                if item.name == '__init__':
                    init_args = method_info.args[1:]
        return ClassSignature(class_name, init_args, methods)

    def extract_code_info(self, code: str) -> ModuleSignature:
        tree = ast.parse(code)
        imports = self.extract_imports(tree)
        import_names = {imp.name for imp in imports} | {spec.name for imp in imports for spec in imp.specified}
        functions = [
            self.extract_function_info(item)
            for item in tree.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        classes = [self.extract_class_info(item) for item in tree.body if isinstance(item, ast.ClassDef)]
        all_defined_names = {func.name for func in functions} | {cls.name for cls in classes}
        for func in functions:
            func.dependencies &= import_names | all_defined_names
            func.dependencies -= {dep for dep in func.dependencies if self.is_std_lib(dep)}
        return ModuleSignature(imports, functions, classes)

    def analyze_file(self) -> ModuleSignature:
        with open(self.file_path, "r", encoding="utf-8") as file:
            code = file.read()
        return self.extract_code_info(code)
