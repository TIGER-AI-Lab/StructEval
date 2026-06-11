from structeval.render_engine.render_react import _normalize_react_source
from structeval.render_engine.render_vue import extract_vue_code_from_tag


def test_react_preserves_default_exported_function():
    source = """
import React, { useState } from 'react';

export default function ReservationForm() {
  const [name, setName] = useState('');
  return <div>{name}</div>;
}
"""

    normalized, export_name = _normalize_react_source(source)

    assert "import React" not in normalized
    assert "function ReservationForm()" in normalized
    assert "return <div>{name}</div>;" in normalized
    assert export_name == "ReservationForm"


def test_react_default_identifier_is_used_for_mounting():
    source = """
import React from 'react';
const Dashboard = () => <section>Dashboard</section>;
export default Dashboard;
"""

    normalized, export_name = _normalize_react_source(source)

    assert "export default" not in normalized
    assert "const Dashboard" in normalized
    assert export_name == "Dashboard"


def test_vue_sfc_export_default_with_semicolon_builds_valid_object():
    source = """
<template>
  <div class="page">Hello</div>
</template>
<script>
export default {
  name: "DemoPage"
};
</script>
<style>
.page { color: red; }
</style>
"""

    component, style = extract_vue_code_from_tag(source)

    assert 'template: "<div class=\\"page\\">Hello</div>"' in component
    assert 'name: "DemoPage"' in component
    assert "export default" not in component
    assert "\\n};" not in component
    assert ".page" in style


def test_vue_fallback_does_not_emit_browser_only_escape_helper():
    component, _ = extract_vue_code_from_tag("plain text `${value}`")

    assert "escapeTemplate" not in component
    assert "plain text" in component
    assert "${value}" in component
