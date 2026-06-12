import importlib.util
import os
import pathlib
import unittest


SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "skills"
    / "os-platform"
    / "scripts"
    / "os_platform.py"
)
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
INSTALL_SCRIPT_PATH = REPO_ROOT / "skills" / "os-platform" / "scripts" / "install.sh"
README_PATH = REPO_ROOT / "README.md"


def load_os_platform():
    spec = importlib.util.spec_from_file_location("os_platform", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class NormalizeBaseUrlTest(unittest.TestCase):
    def setUp(self):
        self.original_base_url = os.environ.pop("OS_PLATFORM_API_BASE_URL", None)
        self.os_platform = load_os_platform()

    def tearDown(self):
        if self.original_base_url is not None:
            os.environ["OS_PLATFORM_API_BASE_URL"] = self.original_base_url
        else:
            os.environ.pop("OS_PLATFORM_API_BASE_URL", None)

    def test_uses_documented_default_when_no_base_url_is_configured(self):
        self.assertEqual(
            self.os_platform.normalize_base_url(None),
            "https://app.opensoftware.co/api",
        )

    def test_environment_base_url_overrides_default(self):
        os.environ["OS_PLATFORM_API_BASE_URL"] = "https://example.test/api/"

        self.assertEqual(
            self.os_platform.normalize_base_url(None),
            "https://example.test/api",
        )

    def test_explicit_base_url_overrides_environment(self):
        os.environ["OS_PLATFORM_API_BASE_URL"] = "https://example.test/api"

        self.assertEqual(
            self.os_platform.normalize_base_url("https://override.test/api/"),
            "https://override.test/api",
        )


class InstallScriptRepositoryTest(unittest.TestCase):
    def test_installer_defaults_to_current_skills_repo(self):
        install_script = INSTALL_SCRIPT_PATH.read_text()

        self.assertIn('DEFAULT_REPO="open-software-network/skills"', install_script)
        self.assertIn(
            "https://raw.githubusercontent.com/open-software-network/skills/main/skills/os-platform/scripts/install.sh",
            install_script,
        )
        self.assertNotIn("open-software-network/agent-skills", install_script)

    def test_readme_installer_url_uses_current_skills_repo(self):
        readme = README_PATH.read_text()

        self.assertIn(
            "https://raw.githubusercontent.com/open-software-network/skills/main/skills/os-platform/scripts/install.sh",
            readme,
        )
        self.assertNotIn("open-software-network/agent-skills", readme)


if __name__ == "__main__":
    unittest.main()
