import importlib.util
import contextlib
import io
import os
import pathlib
import tempfile
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
SKILL_PATH = REPO_ROOT / "skills" / "os-platform" / "SKILL.md"
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

    def test_readme_documents_skills_cli_install(self):
        readme = README_PATH.read_text()

        self.assertIn(
            "npx skills add open-software-network/skills --skill os-platform",
            readme,
        )
        self.assertNotIn("--agent codex --global", readme)

    def test_readme_documents_optional_project_config(self):
        readme = README_PATH.read_text()

        self.assertIn("os-platform.json", readme)
        self.assertIn('"org": "open-software"', readme)
        self.assertIn('"limit": 20', readme)

    def test_skill_documents_agent_routing_policy(self):
        skill = SKILL_PATH.read_text()

        self.assertIn("## Routing Rules", skill)
        self.assertIn("Use the user prompt first, then `os-platform.json`, then ask the user for missing required parameters.", skill)
        self.assertIn("The script is a deterministic read-only tool; do not rely on it to decide user intent.", skill)
        self.assertIn("When the user asks for issues to work on, prioritize todo issues assigned to the user or with no assignee before other todo issues.", skill)
        self.assertIn("When the user asks about a specific issue, fetch the live issue first, then inspect the current local codebase before suggesting implementation work.", skill)
        self.assertIn("Ground suggestions in both the issue data and code references; say when the codebase does not provide enough evidence.", skill)


class ProjectConfigTest(unittest.TestCase):
    def setUp(self):
        self.os_platform = load_os_platform()

    def test_missing_project_config_returns_empty_defaults(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self.os_platform.load_project_config(pathlib.Path(temp_dir))

        self.assertEqual(config, {})

    def test_project_config_is_discovered_from_parent_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            nested = root / "work" / "repo"
            nested.mkdir(parents=True)
            (root / "os-platform.json").write_text('{"org": "open-software", "limit": 7, "ignored": true}')

            config = self.os_platform.load_project_config(nested)

        self.assertEqual(config, {"org": "open-software", "limit": 7})

    def test_project_config_supplies_optional_org_and_limit(self):
        parser = self.os_platform.build_parser()
        args = parser.parse_args(["issues", "list"])

        self.os_platform.apply_project_config(args, {"org": "open-software", "limit": 7})

        method, path, query = self.os_platform.command_to_request(args)
        self.assertEqual(method, "GET")
        self.assertEqual(path, "/v1/orgs/open-software/bounties")
        self.assertEqual(query, {})
        self.assertEqual(args.limit, 7)

    def test_cli_values_override_project_config(self):
        parser = self.os_platform.build_parser()
        args = parser.parse_args(["issues", "list", "other-org", "--limit", "3"])

        self.os_platform.apply_project_config(args, {"org": "open-software", "limit": 7})

        method, path, _ = self.os_platform.command_to_request(args)
        self.assertEqual(method, "GET")
        self.assertEqual(path, "/v1/orgs/other-org/bounties")
        self.assertEqual(args.limit, 3)

    def test_issues_list_without_org_remains_unresolved_for_agent_routing(self):
        parser = self.os_platform.build_parser()
        args = parser.parse_args(["issues", "list"])

        self.os_platform.apply_project_config(args, {})

        self.assertFalse(hasattr(args, "org") and args.org)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.os_platform.command_to_request(args)

    def test_issues_show_uses_config_org_when_only_issue_number_is_supplied(self):
        parser = self.os_platform.build_parser()
        args = parser.parse_args(["issues", "show", "123"])

        self.os_platform.apply_project_config(args, {"org": "open-software"})

        method, path, _ = self.os_platform.command_to_request(args)
        self.assertEqual(method, "GET")
        self.assertEqual(path, "/v1/orgs/open-software/bounties/123")


class IssueSearchCommandTest(unittest.TestCase):
    def setUp(self):
        self.os_platform = load_os_platform()

    def test_issues_search_builds_list_request_with_filters(self):
        parser = self.os_platform.build_parser()
        args = parser.parse_args(
            [
                "issues",
                "search",
                "os-skill",
                "existing issue",
                "--status",
                "todo",
                "--assignee",
                "none",
            ]
        )

        self.os_platform.apply_project_config(args, {})

        method, path, query = self.os_platform.command_to_request(args)
        self.assertEqual(method, "GET")
        self.assertEqual(path, "/v1/orgs/os-skill/bounties")
        self.assertEqual(query, {"status": "todo", "assignee": "none"})
        self.assertEqual(args.search_query, "existing issue")

    def test_issues_list_request_shape_stays_unchanged(self):
        parser = self.os_platform.build_parser()
        args = parser.parse_args(["issues", "list", "os-skill", "--status", "todo"])

        self.os_platform.apply_project_config(args, {})

        method, path, query = self.os_platform.command_to_request(args)
        self.assertEqual(method, "GET")
        self.assertEqual(path, "/v1/orgs/os-skill/bounties")
        self.assertEqual(query, {"status": "todo"})

    def test_search_ranking_prefers_exact_external_id_matches(self):
        issues = [
            {"title": "Add wallet screen", "external_id": "OS2-9"},
            {"title": "Unrelated work", "external_id": "OS2-2"},
            {"title": "Search existing issue", "external_id": "OS2-3"},
        ]

        ranked = self.os_platform.rank_issue_search_results(issues, "OS2-2")

        self.assertEqual([item["external_id"] for item in ranked], ["OS2-2"])

    def test_search_ranking_prefers_exact_title_matches(self):
        issues = [
            {"title": "Existing issue follow-up", "external_id": "OS2-9"},
            {"title": "Search existing issue", "external_id": "OS2-2"},
            {"title": "Existing issue cleanup", "external_id": "OS2-3"},
        ]

        ranked = self.os_platform.rank_issue_search_results(issues, "Search existing issue")

        self.assertEqual(ranked[0]["external_id"], "OS2-2")

    def test_search_ranking_allows_relevant_body_to_beat_unrelated_title(self):
        issues = [
            {
                "title": "Wallet polish",
                "body_markdown": "Unrelated UI cleanup",
                "external_id": "OS2-9",
            },
            {
                "title": "Small helper change",
                "body_markdown": "Search existing issue close to user query",
                "external_id": "OS2-2",
            },
        ]

        ranked = self.os_platform.rank_issue_search_results(issues, "search existing issue")

        self.assertEqual(ranked[0]["external_id"], "OS2-2")

    def test_search_ranking_omits_zero_score_issues(self):
        issues = [
            {"title": "Wallet polish", "body_markdown": "Payment cleanup"},
            {"title": "Search existing issue", "body_markdown": "Find close matches"},
        ]

        ranked = self.os_platform.rank_issue_search_results(issues, "existing issue")

        self.assertEqual([item["title"] for item in ranked], ["Search existing issue"])

    def test_search_payload_is_ranked_before_printing(self):
        parser = self.os_platform.build_parser()
        args = parser.parse_args(["issues", "search", "os-skill", "existing issue"])
        self.os_platform.apply_project_config(args, {})
        payload = {
            "items": [
                {"title": "Wallet polish", "external_id": "OS2-9"},
                {"title": "Search existing issue", "external_id": "OS2-2"},
            ]
        }

        output = self.os_platform.output_data_for_args(payload, args)

        self.assertEqual(output["items"][0]["external_id"], "OS2-2")

    def test_empty_search_query_is_rejected(self):
        parser = self.os_platform.build_parser()
        args = parser.parse_args(["issues", "search", "os-skill", "   "])
        self.os_platform.apply_project_config(args, {})

        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.os_platform.command_to_request(args)


if __name__ == "__main__":
    unittest.main()
