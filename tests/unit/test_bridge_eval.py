"""Tests for bridge eval engine."""

from qt_ai_dev_tools.bridge._eval import MAX_RESULT_BYTES, execute


class TestExecuteEval:
    """Test eval mode (expressions)."""

    def test_simple_expression(self) -> None:
        ns: dict[str, object] = {}
        resp = execute("1 + 1", ns)
        assert resp.ok is True
        assert resp.result == "2"
        assert resp.type_name == "int"

    def test_string_expression(self) -> None:
        ns: dict[str, object] = {}
        resp = execute("'hello'", ns)
        assert resp.ok is True
        assert resp.result == "'hello'"
        assert resp.type_name == "str"

    def test_list_expression(self) -> None:
        ns: dict[str, object] = {}
        resp = execute("[1, 2, 3]", ns)
        assert resp.ok is True
        assert resp.result == "[1, 2, 3]"
        assert resp.type_name == "list"

    def test_namespace_variable(self) -> None:
        ns: dict[str, object] = {"x": 42}
        resp = execute("x * 2", ns)
        assert resp.ok is True
        assert resp.result == "84"

    def test_underscore_updated(self) -> None:
        ns: dict[str, object] = {"_": None}
        execute("42", ns)
        assert ns["_"] == 42

    def test_eval_mode_syntax_error(self) -> None:
        ns: dict[str, object] = {}
        resp = execute("x = 1", ns, mode="eval")
        assert resp.ok is False
        assert "SyntaxError" in (resp.error or "")


class TestExecuteExec:
    """Test exec mode (statements)."""

    def test_assignment(self) -> None:
        ns: dict[str, object] = {}
        resp = execute("x = 42", ns, mode="exec")
        assert resp.ok is True
        assert resp.result is None
        assert ns["x"] == 42

    def test_stdout_capture(self) -> None:
        ns: dict[str, object] = {}
        resp = execute("print('hello')", ns, mode="exec")
        assert resp.ok is True
        assert resp.stdout == "hello\n"

    def test_multiline(self) -> None:
        ns: dict[str, object] = {}
        code = "x = 1\ny = 2\nprint(x + y)"
        resp = execute(code, ns, mode="exec")
        assert resp.ok is True
        assert resp.stdout == "3\n"


class TestExecuteAuto:
    """Test auto mode (eval then exec fallback)."""

    def test_expression_in_auto(self) -> None:
        ns: dict[str, object] = {}
        resp = execute("1 + 1", ns, mode="auto")
        assert resp.ok is True
        assert resp.result == "2"

    def test_statement_in_auto(self) -> None:
        ns: dict[str, object] = {}
        resp = execute("x = 42", ns, mode="auto")
        assert resp.ok is True
        assert ns["x"] == 42

    def test_print_in_auto(self) -> None:
        ns: dict[str, object] = {}
        resp = execute("print('hi')", ns, mode="auto")
        assert resp.ok is True
        # print() is a valid expression (returns None) so eval handles it
        # stdout is captured in both eval and exec modes
        assert resp.stdout == "hi\n"

    def test_runtime_error(self) -> None:
        ns: dict[str, object] = {}
        resp = execute("1 / 0", ns)
        assert resp.ok is False
        assert "ZeroDivisionError" in (resp.error or "")
        assert resp.traceback_str is not None

    def test_name_error(self) -> None:
        ns: dict[str, object] = {}
        resp = execute("undefined_var", ns)
        assert resp.ok is False
        assert "NameError" in (resp.error or "")


class TestTiming:
    def test_duration_populated(self) -> None:
        ns: dict[str, object] = {}
        resp = execute("1+1", ns)
        assert resp.duration_ms >= 0


class TestTruncation:
    def test_large_output_truncated(self) -> None:
        ns: dict[str, object] = {}
        resp = execute(f"'x' * {MAX_RESULT_BYTES + 1000}", ns)
        assert resp.ok is True
        assert resp.result is not None
        assert "[truncated," in resp.result


class TestNamespacePersistence:
    def test_variables_persist_across_calls(self) -> None:
        ns: dict[str, object] = {}
        execute("x = 42", ns)
        resp = execute("x", ns)
        assert resp.ok is True
        assert resp.result == "42"
