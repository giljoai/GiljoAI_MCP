"""
Interactive tests for GiljoAI MCP setup.py script
Tests user interaction flows and input validation
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TestInteractivePrompts(unittest.TestCase):
    """Test interactive user prompts and responses"""

    @patch("builtins.input")
    def test_database_selection_prompt(self, mock_input):
        """Test database type selection interaction"""
        from setup import prompt_database_type

        # Test valid selections
        test_cases = [
            ("1", "sqlite"),
            ("2", "postgresql"),
            ("sqlite", "sqlite"),
            ("postgresql", "postgresql"),
        ]

        for input_val, expected in test_cases:
            mock_input.return_value = input_val
            result = prompt_database_type()
            assert result == expected

    @patch("builtins.input")
    def test_invalid_input_retry(self, mock_input):
        """Test retry mechanism for invalid inputs"""
        from setup import prompt_with_validation

        # First two inputs invalid, third valid
        mock_input.side_effect = ["invalid", "", "valid"]

        def validator(x):
            return x == "valid"

        result = prompt_with_validation("Enter value: ", validator, "Invalid input, please try again")

        assert result == "valid"
        assert mock_input.call_count == 3

    @patch("builtins.input")
    def test_default_value_handling(self, mock_input):
        """Test handling of default values when user presses Enter"""
        from setup import prompt_with_default

        # User presses Enter (empty input)
        mock_input.return_value = ""

        result = prompt_with_default("Enter port", default="6000")

        assert result == "6000"

        # User provides custom value
        mock_input.return_value = "8080"
        result = prompt_with_default("Enter port", default="6000")

        assert result == "8080"

    @patch("getpass.getpass")
    def test_password_input(self, mock_getpass):
        """Test secure password input"""
        from setup import prompt_password

        mock_getpass.return_value = "secure_password123"

        password = prompt_password("Database password")

        assert password == "secure_password123"
        mock_getpass.assert_called_once()

    @patch("builtins.input")
    @patch("getpass.getpass")
    def test_password_confirmation(self, mock_getpass, mock_input):
        """Test password confirmation flow"""
        from setup import prompt_password_with_confirmation

        # Passwords don't match first time
        mock_getpass.side_effect = [
            "password1",  # First entry
            "password2",  # Confirmation (doesn't match)
            "password3",  # Retry first entry
            "password3",  # Retry confirmation (matches)
        ]

        password = prompt_password_with_confirmation()

        assert password == "password3"
        assert mock_getpass.call_count == 4


class TestInputValidationFlows(unittest.TestCase):
    """Test input validation during interactive flows"""

    @patch("builtins.input")
    def test_port_validation_flow(self, mock_input):
        """Test port number validation during input"""
        from setup import prompt_port

        # Invalid ports, then valid
        mock_input.side_effect = [
            "abc",  # Not a number
            "70000",  # Out of range
            "0",  # Invalid port
            "8080",  # Valid
        ]

        port = prompt_port("Enter port")

        assert port == 8080
        assert mock_input.call_count == 4

    @patch("builtins.input")
    def test_path_validation_flow(self, mock_input):
        """Test file path validation during input"""
        from setup import prompt_path

        with tempfile.TemporaryDirectory() as temp_dir:
            valid_path = temp_dir
            invalid_path = "/nonexistent/path"

            # Invalid path, then valid
            mock_input.side_effect = [invalid_path, valid_path]

            path = prompt_path("Enter directory path", must_exist=True)

            assert path == Path(valid_path)
            assert mock_input.call_count == 2

    @patch("builtins.input")
    def test_email_validation_flow(self, mock_input):
        """Test email validation for notifications setup"""
        from setup import prompt_email

        # Invalid emails, then valid
        mock_input.side_effect = [
            "notanemail",
            "missing@",
            "@nodomain",
            "valid@example.com",
        ]

        email = prompt_email("Admin email", required=False)

        assert email == "valid@example.com"

    @patch("builtins.input")
    def test_url_validation_flow(self, mock_input):
        """Test URL validation for API endpoints"""
        from setup import prompt_url

        # Invalid URLs, then valid
        mock_input.side_effect = [
            "not a url",
            "ftp://wrong.protocol",
            "http://valid.url",
        ]

        url = prompt_url("API endpoint", protocols=["http", "https"])

        assert url == "http://valid.url"


class TestConfirmationFlows(unittest.TestCase):
    """Test confirmation prompts and user decisions"""

    @patch("builtins.input")
    @patch("builtins.print")
    def test_configuration_review_flow(self, mock_print, mock_input):
        """Test configuration review and confirmation"""
        from setup import review_and_confirm

        config = {"database": "SQLite", "path": "./data/giljo.db", "ports": {"dashboard": 6000, "api": 6002}}

        # User reviews and confirms
        mock_input.return_value = "y"

        confirmed = review_and_confirm(config)

        assert confirmed

        # Verify configuration was displayed
        print_output = " ".join(str(call) for call in mock_print.call_args_list)
        assert "SQLite" in print_output
        assert "6000" in print_output

    @patch("builtins.input")
    def test_abort_confirmation(self, mock_input):
        """Test abort confirmation when user cancels"""
        from setup import confirm_abort

        # User confirms abort
        mock_input.return_value = "y"
        should_abort = confirm_abort()
        assert should_abort

        # User cancels abort (continues setup)
        mock_input.return_value = "n"
        should_abort = confirm_abort()
        assert not should_abort

    @patch("builtins.input")
    def test_retry_on_error_flow(self, mock_input):
        """Test retry confirmation after error"""
        from setup import prompt_retry_on_error

        error_msg = "Database connection failed"

        # User chooses to retry
        mock_input.return_value = "y"
        should_retry = prompt_retry_on_error(error_msg)
        assert should_retry

        # User chooses not to retry
        mock_input.return_value = "n"
        should_retry = prompt_retry_on_error(error_msg)
        assert not should_retry


class TestMenuNavigation(unittest.TestCase):
    """Test menu navigation and selection"""

    @patch("builtins.input")
    @patch("builtins.print")
    def test_main_menu_navigation(self, mock_print, mock_input):
        """Test main setup menu navigation"""
        from setup import show_main_menu

        # Test each menu option
        menu_selections = [
            ("1", "quick_setup"),
            ("2", "custom_setup"),
            ("3", "migrate"),
            ("4", "help"),
            ("5", "exit"),
        ]

        for input_val, expected_action in menu_selections:
            mock_input.return_value = input_val
            action = show_main_menu()
            assert action == expected_action

    @patch("builtins.input")
    def test_advanced_options_menu(self, mock_input):
        """Test advanced configuration options menu"""
        from setup import show_advanced_menu

        # Select various advanced options
        mock_input.side_effect = [
            "1",  # Configure logging
            "2",  # Configure security
            "3",  # Configure performance
            "4",  # Back to main menu
        ]

        options_selected = []
        for _ in range(4):
            option = show_advanced_menu()
            options_selected.append(option)

        expected = ["logging", "security", "performance", "back"]
        assert options_selected == expected


class TestProgressFeedback(unittest.TestCase):
    """Test progress indicators and user feedback"""

    @patch("builtins.print")
    def test_step_progress_display(self, mock_print):
        """Test step-by-step progress display"""
        from setup import SetupProgress

        progress = SetupProgress(total_steps=5)

        steps = [
            "Checking system requirements",
            "Creating directories",
            "Configuring database",
            "Generating configuration files",
            "Finalizing setup",
        ]

        for step in steps:
            progress.update(step)

        # Verify all steps were displayed
        print_calls = [str(call) for call in mock_print.call_args_list]
        for step in steps:
            assert any(step in call for call in print_calls), f"Step '{step}' not displayed"

        # Verify step numbers were shown
        assert any("[1/5]" in str(call) for call in print_calls)
        assert any("[5/5]" in str(call) for call in print_calls)

    @patch("builtins.print")
    def test_spinner_animation(self, mock_print):
        """Test loading spinner for long operations"""
        from setup import show_spinner

        with patch("time.sleep"):  # Speed up test
            # Show spinner for 2 seconds
            show_spinner("Connecting to database", duration=2)

        # Verify spinner frames were shown
        print_calls = [str(call) for call in mock_print.call_args_list]
        spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

        found_spinner = False
        for char in spinner_chars:
            if any(char in str(call) for call in print_calls):
                found_spinner = True
                break

        assert found_spinner, "Spinner animation not displayed"

    @patch("builtins.print")
    def test_success_failure_messages(self, mock_print):
        """Test success and failure message formatting"""
        from setup import show_result

        # Test success message
        show_result(True, "Database configured successfully")

        # Test failure message
        show_result(False, "Failed to connect to database")

        print_calls = [str(call) for call in mock_print.call_args_list]

        # Verify appropriate formatting/symbols
        assert any("✓" in str(call) or "SUCCESS" in str(call) for call in print_calls)
        assert any("✗" in str(call) or "FAILED" in str(call) for call in print_calls)


class TestHelpSystem(unittest.TestCase):
    """Test help system and documentation display"""

    @patch("builtins.input")
    @patch("builtins.print")
    def test_context_sensitive_help(self, mock_print, mock_input):
        """Test context-sensitive help during setup"""
        from setup import show_help_for_context

        contexts = ["database_selection", "port_configuration", "migration", "troubleshooting"]

        for context in contexts:
            show_help_for_context(context)

            print_output = " ".join(str(call) for call in mock_print.call_args_list)

            # Verify context-specific help was shown
            if context == "database_selection":
                assert "SQLite" in print_output
                assert "PostgreSQL" in print_output
            elif context == "port_configuration":
                assert "6000" in print_output
                assert "6001" in print_output

            mock_print.reset_mock()

    @patch("builtins.input")
    @patch("builtins.print")
    def test_inline_help_prompts(self, mock_print, mock_input):
        """Test inline help available during prompts"""
        from setup import prompt_with_help

        # User asks for help, then provides value
        mock_input.side_effect = ["?", "6000"]

        result = prompt_with_help(
            "Enter dashboard port", help_text="The dashboard port is used for the web interface. Default is 6000."
        )

        assert result == "6000"

        # Verify help was displayed
        print_output = " ".join(str(call) for call in mock_print.call_args_list)
        assert "dashboard port" in print_output
        assert "6000" in print_output


class TestErrorMessages(unittest.TestCase):
    """Test error message clarity and helpfulness"""

    @patch("builtins.print")
    def test_error_message_formatting(self, mock_print):
        """Test error message formatting and clarity"""
        from setup import display_error

        errors = [
            ("Connection refused", "Check that PostgreSQL is running"),
            ("Permission denied", "Try running with administrator privileges"),
            ("Port already in use", "Another service is using this port"),
        ]

        for error, suggestion in errors:
            display_error(error, suggestion)

            print_output = " ".join(str(call) for call in mock_print.call_args_list)

            # Verify error and suggestion are displayed
            assert error in print_output
            assert suggestion in print_output

            mock_print.reset_mock()

    @patch("builtins.print")
    def test_validation_error_messages(self, mock_print):
        """Test validation error message clarity"""
        from setup import ValidationError, display_validation_error

        validations = [
            ("port", "abc", "Port must be a number between 1 and 65535"),
            ("email", "invalid", "Please enter a valid email address"),
            ("path", "/nonexistent", "Path does not exist"),
        ]

        for field, value, expected_msg in validations:
            error = ValidationError(field, value, expected_msg)
            display_validation_error(error)

            print_output = " ".join(str(call) for call in mock_print.call_args_list)
            assert expected_msg in print_output

            mock_print.reset_mock()


if __name__ == "__main__":
    unittest.main()
