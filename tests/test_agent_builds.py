from miosa import (
    create_agent_build_execution_packet,
    create_agent_build_expected_outputs,
    create_build_run_params,
    resolve_agent_build_kind,
)


def test_resolve_agent_build_kind_normalizes_product_labels():
    assert resolve_agent_build_kind("sales page") == "landing_page"
    assert resolve_agent_build_kind("Lead-Magnet") == "lead_magnet"
    assert resolve_agent_build_kind("carousel") == "social_content"
    assert resolve_agent_build_kind("unknown thing") == "custom"


def test_create_agent_build_expected_outputs_for_landing_page():
    contract = create_agent_build_expected_outputs("landing-page")

    assert contract["write_files_under"] == "/workspace/output"
    assert contract["manifest"] == "/workspace/output/manifest.json"
    assert contract["preview_port"] == 3000
    assert {
        "kind": "html",
        "path": "/workspace/output/landing-page.html",
        "mime_type": "text/html",
        "name": "Landing page",
        "previewable": True,
        "downloadable": True,
    } in contract["files"]


def test_create_agent_build_execution_packet_with_planner_markdown():
    packet = create_agent_build_execution_packet(
        run_type="booking",
        title="New Patient Booking Page",
        goal="Create a conversion-focused booking page for a dental office.",
        context_markdown="# Doctor\nDr. Ray",
        planner_documents=[
            {
                "kind": "brand_voice",
                "title": "Brand Voice",
                "contentMarkdown": "Warm, expert, direct.",
            }
        ],
        input_refs=[
            {
                "kind": "inline_text",
                "title": "Calendar embed code",
                "text": "<iframe src='https://calendar.example.com'></iframe>",
            }
        ],
        quality_rules=["Use provided brand colors.", "Write a manifest."],
        metadata={"workspace_id": "clinic_ws_1"},
    )

    assert packet["build_kind"] == "booking_page"
    assert packet["deliverable_type"] == "booking_page"
    assert packet["input_refs"][0]["title"] == "Calendar embed code"
    assert packet["runtime_instructions"]["input_materialization"]["directory"] == (
        "/workspace/inputs"
    )
    assert packet["metadata"]["workspace_id"] == "clinic_ws_1"
    assert packet["metadata"]["input_refs"] == packet["input_refs"]
    assert packet["metadata"]["design_research_required"] is True
    assert packet["planner_documents"][0]["content_markdown"] == "Warm, expert, direct."
    assert packet["expected_outputs"]["preview_port"] == 3000


def test_create_build_run_params_ready_for_runs_run():
    params = create_build_run_params(
        sandbox_id="sbx_123",
        agent_runtime_profile_id="arp_claude",
        external_workspace_id="clinic_ws_1",
        external_user_id="doctor_1",
        external_project_id="project_1",
        run_type="lead magnet",
        title="Implant Readiness Guide",
        goal="Build a downloadable lead magnet.",
        model="claude-opus-4.8",
    )

    assert params["target_kind"] == "sandbox"
    assert params["sandbox_id"] == "sbx_123"
    assert params["runner"] == "claude-code"
    assert params["model"] == "claude-opus-4.8"
    assert params["agent_runtime_profile_id"] == "arp_claude"
    assert params["external_workspace_id"] == "clinic_ws_1"
    assert params["external_user_id"] == "doctor_1"
    assert params["external_project_id"] == "project_1"
    assert params["approval_policy"] == {
        "publish": "manual",
        "external_write": "manual",
        "destructive_actions": "forbidden",
    }
    assert params["capability_requirements"] == ["filesystem", "shell", "files", "downloads"]
    assert params["execution_packet"]["build_kind"] == "lead_magnet"
    assert params["execution_packet"]["deliverable_type"] == "lead_magnet"
    assert params["execution_packet"]["runtime_profile_id"] == "arp_claude"
    assert "Build: Implant Readiness Guide" in params["instruction"]
