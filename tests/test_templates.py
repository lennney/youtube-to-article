"""Tests for template system."""
import tempfile
from pathlib import Path
from ytarticle.templates.base import resolve_template, list_templates


class TestTemplateResolver:
    def test_default_template_resolves(self):
        template_dir, template_name = resolve_template("default")
        assert (template_dir / template_name).exists()

    def test_diyhub_template_resolves(self):
        template_dir, template_name = resolve_template("diyhub")
        assert (template_dir / template_name).exists()

    def test_custom_dir_takes_priority(self):
        with tempfile.TemporaryDirectory() as td:
            custom_dir = Path(td)
            tmpl_dir = custom_dir / "custom"
            tmpl_dir.mkdir(parents=True)
            tmpl_file = tmpl_dir / "my_template.html"
            tmpl_file.write_text("<html></html>")

            resolved_dir, resolved_name = resolve_template("custom/my_template.html",
                                                           custom_dirs=[str(custom_dir)])
            assert resolved_name == "custom/my_template.html"

    def test_list_templates(self):
        names = list_templates()
        assert "default" in names
        assert "diyhub" in names
