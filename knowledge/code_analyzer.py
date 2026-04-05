"""
Code Analyzer - Analyze and suggest improvements for code snippets.
"""

import ast
import logging
import os
import re
from typing import Dict, List, Optional

from utils.config import Config

logger = logging.getLogger(__name__)


class CodeAnalyzer:
    """
    Analyzes code for:
    - Syntax errors (Python AST parsing)
    - Code quality issues
    - Complexity metrics
    - Style suggestions
    - Documentation coverage
    """

    def __init__(self, config: Config):
        self.config = config

    # ------------------------------------------------------------------
    # Python Analysis
    # ------------------------------------------------------------------

    def analyze_python(self, code: str) -> Dict:
        """Comprehensive Python code analysis."""
        result: Dict = {
            "language": "python",
            "syntax_valid": False,
            "errors": [],
            "warnings": [],
            "metrics": {},
            "suggestions": [],
        }

        # Syntax check
        try:
            tree = ast.parse(code)
            result["syntax_valid"] = True
        except SyntaxError as e:
            result["errors"].append(f"SyntaxError at line {e.lineno}: {e.msg}")
            return result

        # Metrics
        lines = code.splitlines()
        result["metrics"] = {
            "total_lines": len(lines),
            "blank_lines": sum(1 for l in lines if not l.strip()),
            "comment_lines": sum(1 for l in lines if l.strip().startswith("#")),
            "functions": len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]),
            "classes": len([n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]),
            "imports": len([n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]),
        }

        # Complexity check (function length)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_lines = node.end_lineno - node.lineno + 1 if hasattr(node, "end_lineno") else 0
                if func_lines > 50:
                    result["warnings"].append(
                        f"Function '{node.name}' is {func_lines} lines long — consider refactoring"
                    )

        # Style suggestions
        suggestions = self._python_style_check(code)
        result["suggestions"].extend(suggestions)

        # Documentation
        has_module_doc = isinstance(tree.body[0], ast.Expr) if tree.body else False
        if not has_module_doc:
            result["suggestions"].append("Add a module-level docstring")

        undocumented_funcs = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and not (node.body and isinstance(node.body[0], ast.Expr))
        ]
        if undocumented_funcs:
            result["suggestions"].append(
                f"Undocumented functions: {', '.join(undocumented_funcs[:5])}"
            )

        return result

    def _python_style_check(self, code: str) -> List[str]:
        """Check for common Python style issues."""
        suggestions = []
        lines = code.splitlines()
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                suggestions.append(f"Line {i} exceeds 120 characters")
            if "  " in line and not line.startswith("  "):
                pass  # Skip indentation
            if re.search(r"\bexcept\s*:", line):
                suggestions.append(f"Line {i}: Bare 'except:' clause — be specific about exception types")
            if re.search(r"import \*", line):
                suggestions.append(f"Line {i}: Wildcard import — import specific names instead")
        return suggestions[:10]

    # ------------------------------------------------------------------
    # Generic Analysis
    # ------------------------------------------------------------------

    def analyze_file(self, filepath: str) -> Optional[Dict]:
        """Analyze a source file by extension."""
        if not os.path.exists(filepath):
            return {"error": f"File not found: {filepath}"}

        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            code = f.read()

        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".py":
            result = self.analyze_python(code)
        else:
            result = self._generic_analysis(code, ext)

        result["file"] = filepath
        result["size_bytes"] = os.path.getsize(filepath)
        return result

    def _generic_analysis(self, code: str, extension: str) -> Dict:
        """Basic analysis for non-Python files."""
        lines = code.splitlines()
        return {
            "language": extension.lstrip("."),
            "total_lines": len(lines),
            "blank_lines": sum(1 for l in lines if not l.strip()),
            "syntax_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": [],
        }

    # ------------------------------------------------------------------
    # Complexity (McCabe)
    # ------------------------------------------------------------------

    def cyclomatic_complexity(self, code: str) -> Dict:
        """Estimate cyclomatic complexity for Python functions."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {}

        results = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Count decision points
                complexity = 1
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler,
                                         ast.With, ast.Assert, ast.comprehension)):
                        complexity += 1
                    elif isinstance(child, ast.BoolOp):
                        complexity += len(child.values) - 1
                results[node.name] = complexity
        return results
