import os
import sys

sys.path.insert(0, os.path.abspath("../src"))

project = "ChainRight"
copyright = "2024, David Adams"
author = "David Adams"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_theme_options = {
    "repository_url": "https://github.com/davidatoms/ChainRight",
    "use_repository_button": True,
}

intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}

myst_enable_extensions = ["colon_fence", "deflist"]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
