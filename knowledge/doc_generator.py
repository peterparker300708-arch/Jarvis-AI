"""
Documentation Generator - Auto-generate documentation from Python code.
"""

import ast
import inspect
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from utils.config import Config

logger = logging.getLogger(__name__)


class DocGenerator:
    """
    Automatically generates Markdown and HTML documentation from:
    - Python source files (using AST)
    - Existing docstrings
    - README templates
    """

    def __init__(self, config: Config):
        self.config = config
        self.output_dir = config.get("paths.docs", "docs")
        os.makedirs(self.output_dir, exist_ok=True)

    # ------------------------------------------------------------------

    def document_file(self, filepath: str) -> Dict:
        """Parse a Python file and extract documentation metadata."""
        if not os.path.exists(filepath):
            return {"error": f"File not found: {filepath}"}

        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return {"error": f"Syntax error: {e}"}

        module_doc = ast.get_docstring(tree) or ""
        functions = []
        classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_doc = ast.get_docstring(node) or ""
                args = [a.arg for a in node.args.args]
                functions.append(
                    {
                        "name": node.name,
                        "docstring": func_doc,
                        "args": args,
                        "lineno": node.lineno,
                        "is_public": not node.name.startswith("_"),
                    }
                )
            elif isinstance(node, ast.ClassDef):
                class_doc = ast.get_docstring(node) or ""
                methods = []
                for child in ast.walk(node):
                    if isinstance(child, ast.FunctionDef):
                        method_doc = ast.get_docstring(child) or ""
                        methods.append(
                            {
                                "name": child.name,
                                "docstring": method_doc,
                                "is_public": not child.name.startswith("_"),
                            }
                        )
                classes.append(
                    {
                        "name": node.name,
                        "docstring": class_doc,
                        "methods": methods,
                        "lineno": node.lineno,
                    }
                )

        return {
            "file": filepath,
            "module_docstring": module_doc,
            "functions": functions,
            "classes": classes,
        }

    def generate_markdown(self, metadata: Dict) -> str:
        """Convert documentation metadata to Markdown."""
        lines = []
        filepath = metadata.get("file", "")
        module_name = Path(filepath).stem if filepath else "Module"
        lines.append(f"# {module_name}\n")

        module_doc = metadata.get("module_docstring", "")
        if module_doc:
            lines.append(f"{module_doc}\n")

        # Classes
        for cls in metadata.get("classes", []):
            lines.append(f"## class `{cls['name']}`\n")
            if cls["docstring"]:
                lines.append(f"{cls['docstring']}\n")
            pub_methods = [m for m in cls["methods"] if m["is_public"]]
            if pub_methods:
                lines.append("### Methods\n")
                for method in pub_methods:
                    lines.append(f"#### `{method['name']}()`")
                    if method["docstring"]:
                        lines.append(f"\n{method['docstring']}\n")
                    else:
                        lines.append("\n*No documentation available*\n")

        # Top-level functions
        pub_funcs = [f for f in metadata.get("functions", []) if f["is_public"]]
        if pub_funcs:
            lines.append("## Functions\n")
            for func in pub_funcs:
                args_str = ", ".join(func["args"])
                lines.append(f"### `{func['name']}({args_str})`\n")
                if func["docstring"]:
                    lines.append(f"{func['docstring']}\n")

        return "\n".join(lines)

    def document_project(self, source_dir: str = ".") -> List[str]:
        """Document all Python files in a directory."""
        docs_files = []
        for py_file in Path(source_dir).rglob("*.py"):
            if any(part.startswith((".", "_")) for part in py_file.parts):
                continue
            metadata = self.document_file(str(py_file))
            if "error" in metadata:
                continue
            markdown = self.generate_markdown(metadata)
            out_name = py_file.stem + ".md"
            out_path = os.path.join(self.output_dir, out_name)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(markdown)
            docs_files.append(out_path)
        return docs_files

    def generate_readme(self, project_name: str, description: str, features: List[str]) -> str:
        """Generate a README.md template."""
        badge_line = f"![Python](https://img.shields.io/badge/python-3.9+-blue)"
        feature_list = "\n".join(f"- ✅ {f}" for f in features)
        readme = f"""# {project_name}

{badge_line}

{description}

## Features

{feature_list}

## Quick Start

```bash
git clone <repo-url>
cd {project_name.lower().replace(' ', '-')}
pip install -r requirements.txt
python jarvis.py
```

## Documentation

See the [docs/](docs/) directory for full documentation.

## License

MIT License
"""
        return readme
