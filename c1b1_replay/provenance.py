"""Approval binds source and dependency bytes. Fingerprints are not raw-state equality."""
import ast
import hashlib
from pathlib import Path
import platform
import mpmath

FORBIDDEN={"a_reference","a_numeric","engine","audit"}

def independence():
    violations=[]
    for path in sorted(Path(__file__).parent.glob("*.py")):
        tree=ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names=[]
            if isinstance(node,ast.Import):
                names=[a.name for a in node.names]
            elif isinstance(node,ast.ImportFrom) and node.level==0:
                names=[node.module or ""]
            for name in names:
                if name.split(".")[0] in FORBIDDEN:
                    violations.append(f"{path.name}:{node.lineno}:{name}")
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in ("__import__","eval","exec"):
                violations.append(f"{path.name}:{node.lineno}:dynamic code import")
    return tuple(violations)

def source_hash(paths,root):
    digest=hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(root).as_posix().encode()+b"\0")
        digest.update(path.read_bytes().replace(b"\r\n",b"\n")+b"\0")
    return digest.hexdigest()

def fingerprints():
    root=Path(__file__).parent
    implementation=source_hash(root.glob("*.py"),root)
    dependency_root=Path(mpmath.__file__).parent
    dependency=hashlib.sha256((mpmath.__version__+"|"+platform.python_implementation()+"|"+
        platform.python_version()+"|"+str(mpmath.libmp.BACKEND)+"|"+
        source_hash(dependency_root.rglob("*.py"),dependency_root)).encode()).hexdigest()
    return implementation,dependency
