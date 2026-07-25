"""Helpers for building MIOSA agent execution packets.

These helpers are transport-free. Product backends can assemble a packet with
chat context, uploaded files, planner markdown, and output expectations, then
pass it to ``client.runs.run``.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal, TypedDict, cast

AgentBuildKind = Literal[
    "landing_page",
    "website",
    "lead_magnet",
    "webinar",
    "slides_deck",
    "email_sequence",
    "social_content",
    "ad_creative",
    "booking_page",
    "brand_identity",
    "offer",
    "program",
    "podcast",
    "sales_script",
    "campaign",
    "challenge",
    "character",
    "custom",
]

DEFAULT_AGENT_BUILD_PACKET_VERSION = "2026-06-19"
DEFAULT_AGENT_BUILD_OUTPUT_ROOT = "/workspace/output"
DEFAULT_AGENT_BUILD_INPUT_ROOT = "/workspace/inputs"


class AgentBuildFileSpec(TypedDict, total=False):
    kind: str
    path: str
    mime_type: str
    name: str
    downloadable: bool
    previewable: bool
    required: bool


class AgentBuildInputRef(TypedDict, total=False):
    kind: str
    title: str
    ref: str
    file_ref: str
    drive_asset_id: str
    filename: str
    content_type: str
    size_bytes: int
    public_url: str
    text: str
    path: str
    metadata: dict[str, Any]


class AgentBuildKindSpec(TypedDict):
    kind: AgentBuildKind
    label: str
    deliverable_type: str
    runtime_template: dict[str, Any]
    requested_outputs: list[str]
    planner_document_kinds: list[str]
    files: list[AgentBuildFileSpec]
    design_research_required: bool
    preview_port: int | None


class AgentBuildPlannerDocument(TypedDict, total=False):
    kind: str
    title: str
    content_markdown: str
    contentMarkdown: str
    path: str
    metadata: dict[str, Any]


COMMON_PLANNER_DOCUMENT_KINDS = [
    "input_bundle",
    "client_grounding",
    "brand_identity",
    "strategy_context",
    "quality_rules",
]

NEXTJS_RUNTIME_TEMPLATE: dict[str, Any] = {
    "kind": "nextjs_app",
    "template_id": "nextjs",
    "workspace_root": "/workspace",
    "app_dir": "/workspace/app",
    "output_dir": DEFAULT_AGENT_BUILD_OUTPUT_ROOT,
    "expected_preview_port": 3000,
    "start_command": "npm run dev -- --hostname 0.0.0.0 --port 3000",
    "build_command": "npm run build",
}


def _file_bundle(kind: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "workspace_root": "/workspace",
        "output_dir": DEFAULT_AGENT_BUILD_OUTPUT_ROOT,
    }


def _spec(
    kind: AgentBuildKind,
    label: str,
    deliverable_type: str,
    runtime_template: dict[str, Any],
    files: list[AgentBuildFileSpec],
    *,
    requested_outputs: list[str] | None = None,
    planner_document_kinds: list[str] | None = None,
    design_research_required: bool = False,
    preview_port: int | None = None,
) -> AgentBuildKindSpec:
    return {
        "kind": kind,
        "label": label,
        "deliverable_type": deliverable_type,
        "runtime_template": runtime_template,
        "requested_outputs": requested_outputs or ["requested deliverables", "manifest"],
        "planner_document_kinds": planner_document_kinds or COMMON_PLANNER_DOCUMENT_KINDS,
        "files": files,
        "design_research_required": design_research_required,
        "preview_port": preview_port,
    }


BUILD_KIND_ALIASES: dict[str, AgentBuildKind] = {
    "ad": "ad_creative",
    "ads": "ad_creative",
    "adcreative": "ad_creative",
    "ad_creative": "ad_creative",
    "booking": "booking_page",
    "booking_form": "booking_page",
    "booking_page": "booking_page",
    "brand": "brand_identity",
    "brand_character": "character",
    "brand_identity": "brand_identity",
    "campaign": "campaign",
    "campaign_plan": "campaign",
    "carousel": "social_content",
    "challenge": "challenge",
    "character": "character",
    "character_pack": "character",
    "content": "social_content",
    "content_batch": "social_content",
    "course": "program",
    "email": "email_sequence",
    "email_sequence": "email_sequence",
    "email_sms_sequence": "email_sequence",
    "funnel": "landing_page",
    "landing": "landing_page",
    "landing_page": "landing_page",
    "lead_magnet": "lead_magnet",
    "leadmagnet": "lead_magnet",
    "offer": "offer",
    "offer_stack": "offer",
    "online_course": "program",
    "page": "landing_page",
    "podcast": "podcast",
    "podcast_audio": "podcast",
    "program": "program",
    "sales_page": "landing_page",
    "sales_script": "sales_script",
    "sales_script_builder": "sales_script",
    "salesscript": "sales_script",
    "site": "website",
    "slides": "slides_deck",
    "slides_deck": "slides_deck",
    "social": "social_content",
    "social_content": "social_content",
    "social_media": "social_content",
    "social_media_post": "social_content",
    "text_card": "social_content",
    "webinar": "webinar",
    "website": "website",
}


AGENT_BUILD_KIND_SPECS: dict[AgentBuildKind, AgentBuildKindSpec] = {
    "landing_page": _spec(
        "landing_page",
        "Landing page",
        "landing_page",
        NEXTJS_RUNTIME_TEMPLATE,
        [
            {
                "kind": "html",
                "path": "landing-page.html",
                "mime_type": "text/html",
                "name": "Landing page",
                "previewable": True,
            },
            {
                "kind": "source",
                "path": "source.zip",
                "mime_type": "application/zip",
                "name": "Source files",
            },
        ],
        requested_outputs=["Next.js landing page", "preview URL", "source files"],
        design_research_required=True,
        preview_port=3000,
    ),
    "website": _spec(
        "website",
        "Website",
        "website",
        NEXTJS_RUNTIME_TEMPLATE,
        [
            {
                "kind": "html",
                "path": "website.html",
                "mime_type": "text/html",
                "name": "Website",
                "previewable": True,
            },
            {
                "kind": "source",
                "path": "source.zip",
                "mime_type": "application/zip",
                "name": "Source files",
            },
        ],
        requested_outputs=["Next.js website", "preview URL", "source files"],
        design_research_required=True,
        preview_port=3000,
    ),
    "lead_magnet": _spec(
        "lead_magnet",
        "Lead magnet",
        "lead_magnet",
        NEXTJS_RUNTIME_TEMPLATE,
        [
            {
                "kind": "pdf",
                "path": "lead-magnet.pdf",
                "mime_type": "application/pdf",
                "name": "Lead magnet PDF",
                "previewable": True,
            },
            {
                "kind": "html",
                "path": "opt-in-page.html",
                "mime_type": "text/html",
                "name": "Opt-in page",
                "previewable": True,
            },
        ],
        requested_outputs=["PDF lead magnet", "opt-in page", "source files"],
        design_research_required=True,
        preview_port=3000,
    ),
    "webinar": _spec(
        "webinar",
        "Webinar",
        "webinar",
        NEXTJS_RUNTIME_TEMPLATE,
        [
            {
                "kind": "html",
                "path": "webinar-page.html",
                "mime_type": "text/html",
                "name": "Webinar page",
                "previewable": True,
            },
            {
                "kind": "markdown",
                "path": "webinar-script.md",
                "mime_type": "text/markdown",
                "name": "Webinar script",
            },
        ],
        design_research_required=True,
        preview_port=3000,
    ),
    "slides_deck": _spec(
        "slides_deck",
        "Slides deck",
        "slides_deck",
        _file_bundle("html_deck"),
        [
            {
                "kind": "html",
                "path": "deck.html",
                "mime_type": "text/html",
                "name": "Slide deck",
                "previewable": True,
            }
        ],
        design_research_required=True,
    ),
    "email_sequence": _spec(
        "email_sequence",
        "Email sequence",
        "email_sms_sequence",
        _file_bundle("email_bundle"),
        [
            {
                "kind": "markdown",
                "path": "email-sequence.md",
                "mime_type": "text/markdown",
                "name": "Email sequence",
                "previewable": True,
            }
        ],
    ),
    "social_content": _spec(
        "social_content",
        "Social content",
        "social_media_post",
        _file_bundle("html_image_bundle"),
        [
            {
                "kind": "html",
                "path": "social-carousel.html",
                "mime_type": "text/html",
                "name": "Social carousel",
                "previewable": True,
            },
            {
                "kind": "markdown",
                "path": "captions.md",
                "mime_type": "text/markdown",
                "name": "Caption bank",
            },
        ],
        design_research_required=True,
    ),
    "ad_creative": _spec(
        "ad_creative",
        "Ad creative",
        "ad_creative",
        _file_bundle("html_image_bundle"),
        [
            {
                "kind": "html",
                "path": "ad-creative.html",
                "mime_type": "text/html",
                "name": "Ad creative previews",
                "previewable": True,
            }
        ],
        design_research_required=True,
    ),
    "booking_page": _spec(
        "booking_page",
        "Booking page",
        "booking_page",
        NEXTJS_RUNTIME_TEMPLATE,
        [
            {
                "kind": "html",
                "path": "booking-page.html",
                "mime_type": "text/html",
                "name": "Booking page",
                "previewable": True,
            }
        ],
        requested_outputs=["booking page", "confirmation copy", "source files"],
        design_research_required=True,
        preview_port=3000,
    ),
    "brand_identity": _spec(
        "brand_identity",
        "Brand identity",
        "brand_identity",
        _file_bundle("brand_bundle"),
        [
            {
                "kind": "markdown",
                "path": "brand-guide.md",
                "mime_type": "text/markdown",
                "name": "Brand guide",
                "previewable": True,
            }
        ],
        design_research_required=True,
    ),
    "offer": _spec(
        "offer",
        "Offer",
        "offer",
        _file_bundle("offer_bundle"),
        [
            {
                "kind": "markdown",
                "path": "offer-stack.md",
                "mime_type": "text/markdown",
                "name": "Offer stack",
                "previewable": True,
            }
        ],
    ),
    "program": _spec(
        "program",
        "Program",
        "program_lms",
        _file_bundle("program_lms"),
        [
            {
                "kind": "html",
                "path": "program.html",
                "mime_type": "text/html",
                "name": "Program preview",
                "previewable": True,
            },
            {
                "kind": "markdown",
                "path": "program.md",
                "mime_type": "text/markdown",
                "name": "Program outline",
            },
        ],
        design_research_required=True,
    ),
    "podcast": _spec(
        "podcast",
        "Podcast",
        "podcast_audio",
        _file_bundle("podcast_audio"),
        [
            {
                "kind": "html",
                "path": "podcast.html",
                "mime_type": "text/html",
                "name": "Podcast preview",
                "previewable": True,
            },
            {
                "kind": "markdown",
                "path": "show-notes.md",
                "mime_type": "text/markdown",
                "name": "Show notes",
            },
        ],
    ),
    "sales_script": _spec(
        "sales_script",
        "Sales script",
        "sales_script",
        _file_bundle("script_bundle"),
        [
            {
                "kind": "markdown",
                "path": "sales-script.md",
                "mime_type": "text/markdown",
                "name": "Sales script",
                "previewable": True,
            }
        ],
    ),
    "campaign": _spec(
        "campaign",
        "Campaign",
        "campaign",
        _file_bundle("campaign_bundle"),
        [
            {
                "kind": "markdown",
                "path": "campaign-plan.md",
                "mime_type": "text/markdown",
                "name": "Campaign plan",
                "previewable": True,
            },
            {
                "kind": "html",
                "path": "campaign-assets.html",
                "mime_type": "text/html",
                "name": "Campaign assets",
                "previewable": True,
            },
        ],
        design_research_required=True,
    ),
    "challenge": _spec(
        "challenge",
        "Challenge",
        "challenge",
        _file_bundle("challenge_bundle"),
        [
            {
                "kind": "markdown",
                "path": "challenge-plan.md",
                "mime_type": "text/markdown",
                "name": "Challenge plan",
                "previewable": True,
            }
        ],
    ),
    "character": _spec(
        "character",
        "Character pack",
        "brand_character",
        _file_bundle("character_bundle"),
        [
            {
                "kind": "markdown",
                "path": "character-pack.md",
                "mime_type": "text/markdown",
                "name": "Character pack",
                "previewable": True,
            }
        ],
        design_research_required=True,
    ),
    "custom": _spec(
        "custom",
        "Custom build",
        "file_bundle",
        _file_bundle("file_bundle"),
        [],
    ),
}


def _normalize_build_kind(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    return "".join(char if char.isalnum() or char == "_" else "" for char in normalized)


def resolve_agent_build_kind(
    value: str | None, fallback: AgentBuildKind = "custom"
) -> AgentBuildKind:
    normalized = "_".join(part for part in _normalize_build_kind(value).split("_") if part)
    if not normalized:
        return fallback
    return BUILD_KIND_ALIASES.get(normalized, fallback)


def get_agent_build_kind_spec(value: str | None) -> AgentBuildKindSpec:
    return deepcopy(AGENT_BUILD_KIND_SPECS[resolve_agent_build_kind(value)])


def _file_path(path: str, output_root: str) -> str:
    return path if path.startswith("/") else f"{output_root}/{path}"


def create_agent_build_expected_outputs(
    build_kind: str | None,
    *,
    deliverable_type: str | None = None,
    files: list[AgentBuildFileSpec] | None = None,
    expected_outputs: dict[str, Any] | None = None,
    output_root: str = DEFAULT_AGENT_BUILD_OUTPUT_ROOT,
) -> dict[str, Any]:
    if expected_outputs is not None:
        return expected_outputs
    spec = AGENT_BUILD_KIND_SPECS[resolve_agent_build_kind(build_kind)]
    normalized_files: list[dict[str, Any]] = [
        {
            "path": f"{output_root}/manifest.json",
            "kind": "json",
            "mime_type": "application/json",
            "name": "Manifest",
            "downloadable": True,
        }
    ]
    for file_spec in files or spec["files"]:
        item = dict(file_spec)
        item["path"] = _file_path(str(item["path"]), output_root)
        item.setdefault("downloadable", True)
        normalized_files.append(item)

    contract: dict[str, Any] = {
        "write_files_under": output_root,
        "manifest": f"{output_root}/manifest.json",
        "planner_documents_under": "/workspace/planner",
        "inputs_under": DEFAULT_AGENT_BUILD_INPUT_ROOT,
        "deliverable_type": deliverable_type or spec["deliverable_type"],
        "required_files": [f"{output_root}/manifest.json"],
        "files": normalized_files,
        "expected_outputs": {
            "messages": True,
            "files": normalized_files,
            "previews": spec["preview_port"] is not None,
        },
        "include_downloads": True,
    }
    if spec["preview_port"] is not None:
        contract["preview_port"] = spec["preview_port"]
    return contract


def _normalize_planner_documents(
    documents: list[AgentBuildPlannerDocument] | None,
) -> list[dict[str, Any]]:
    normalized = []
    for document in documents or []:
        entry = dict(document)
        entry["content_markdown"] = (
            entry.get("content_markdown") or entry.get("contentMarkdown") or ""
        )
        normalized.append(entry)
    return normalized


def create_agent_build_execution_packet(
    *,
    title: str,
    goal: str,
    run_type: str | None = None,
    build_kind: str | None = None,
    deliverable_type: str | None = None,
    context_markdown: str = "",
    planner_documents: list[AgentBuildPlannerDocument] | None = None,
    requested_outputs: list[str] | None = None,
    quality_rules: list[str] | None = None,
    source_refs: list[Any] | None = None,
    input_refs: list[AgentBuildInputRef] | None = None,
    runtime_profile_id: str | None = None,
    runtime_template: dict[str, Any] | None = None,
    expected_outputs: dict[str, Any] | None = None,
    files: list[AgentBuildFileSpec] | None = None,
    output_root: str = DEFAULT_AGENT_BUILD_OUTPUT_ROOT,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved = resolve_agent_build_kind(build_kind or run_type)
    spec = AGENT_BUILD_KIND_SPECS[resolved]
    resolved_deliverable_type = deliverable_type or spec["deliverable_type"]
    resolved_template = runtime_template or spec["runtime_template"]
    normalized_inputs = [dict(item) for item in input_refs or []]
    resolved_expected_outputs = create_agent_build_expected_outputs(
        resolved,
        deliverable_type=resolved_deliverable_type,
        files=files,
        expected_outputs=expected_outputs,
        output_root=output_root,
    )
    packet: dict[str, Any] = {
        "version": DEFAULT_AGENT_BUILD_PACKET_VERSION,
        "run_type": resolved,
        "build_kind": resolved,
        "deliverable_type": resolved_deliverable_type,
        "title": title,
        "goal": goal,
        "source_refs": source_refs or [],
        "input_refs": normalized_inputs,
        "context_markdown": context_markdown,
        "planner_documents": _normalize_planner_documents(planner_documents),
        "requested_outputs": requested_outputs or list(spec["requested_outputs"]),
        "quality_rules": quality_rules or [],
        "expected_outputs": resolved_expected_outputs,
        "runtime_instructions": {
            "agent": "claude",
            "template": resolved_template,
            "input_materialization": {
                "directory": DEFAULT_AGENT_BUILD_INPUT_ROOT,
                "manifest": f"{DEFAULT_AGENT_BUILD_INPUT_ROOT}/inputs.json",
            },
            "design_research": {
                "provider": "refero",
                "required": spec["design_research_required"],
            },
        },
        "metadata": {
            **(metadata or {}),
            "build_kind": resolved,
            "deliverable_type": resolved_deliverable_type,
            "build_target": resolved_template,
            "runtime_template": resolved_template,
            "expected_outputs": resolved_expected_outputs,
            "input_refs": normalized_inputs,
            "design_research_required": spec["design_research_required"],
            "planner_document_kinds": list(spec["planner_document_kinds"]),
        },
    }
    if runtime_profile_id:
        packet["runtime_profile_id"] = runtime_profile_id
    return packet


def create_agent_build_instruction(packet: dict[str, Any]) -> str:
    expected_outputs = cast(dict[str, Any], packet.get("expected_outputs") or {})
    return "\n".join(
        [
            f"Build: {packet.get('title', 'Untitled build')}",
            "",
            str(packet.get("goal") or ""),
            "",
            f"Materialize input_refs under {DEFAULT_AGENT_BUILD_INPUT_ROOT}.",
            "Use the execution packet, input bundle, planner documents, "
            "brand/context notes, and quality rules.",
            f"Write every deliverable under {expected_outputs.get('write_files_under')}.",
            f"Write a JSON manifest to {expected_outputs.get('manifest')}.",
            "Do not expose secrets. Do not publish externally unless the approval "
            "policy allows it.",
        ]
    )


def create_build_run_params(
    *,
    title: str,
    goal: str,
    run_type: str | None = None,
    build_kind: str | None = None,
    deliverable_type: str | None = None,
    target_kind: str | None = None,
    target_id: str | None = None,
    sandbox_id: str | None = None,
    computer_id: str | None = None,
    runner: str = "claude-code",
    provider: str | None = None,
    model: str | None = None,
    instruction: str | None = None,
    cwd: str = "/workspace",
    timeout: int = 1800,
    wait: bool = False,
    env: dict[str, str] | None = None,
    agent_runtime_profile_id: str | None = None,
    runtime_profile_id: str | None = None,
    external_workspace_id: str | None = None,
    external_user_id: str | None = None,
    external_project_id: str | None = None,
    context_markdown: str = "",
    planner_documents: list[AgentBuildPlannerDocument] | None = None,
    requested_outputs: list[str] | None = None,
    quality_rules: list[str] | None = None,
    source_refs: list[Any] | None = None,
    input_refs: list[AgentBuildInputRef] | None = None,
    runtime_template: dict[str, Any] | None = None,
    expected_outputs: dict[str, Any] | None = None,
    files: list[AgentBuildFileSpec] | None = None,
    output_root: str = DEFAULT_AGENT_BUILD_OUTPUT_ROOT,
    metadata: dict[str, Any] | None = None,
    approval_policy: dict[str, Any] | None = None,
    capability_requirements: list[str] | None = None,
) -> dict[str, Any]:
    profile_id = agent_runtime_profile_id or runtime_profile_id
    packet = create_agent_build_execution_packet(
        title=title,
        goal=goal,
        run_type=run_type,
        build_kind=build_kind,
        deliverable_type=deliverable_type,
        context_markdown=context_markdown,
        planner_documents=planner_documents,
        requested_outputs=requested_outputs,
        quality_rules=quality_rules,
        source_refs=source_refs,
        input_refs=input_refs,
        runtime_profile_id=profile_id,
        runtime_template=runtime_template,
        expected_outputs=expected_outputs,
        files=files,
        output_root=output_root,
        metadata=metadata,
    )
    body: dict[str, Any] = {
        "instruction": instruction or create_agent_build_instruction(packet),
        "target_kind": target_kind or ("computer" if computer_id else "sandbox"),
        "target_id": target_id,
        "sandbox_id": sandbox_id,
        "computer_id": computer_id,
        "runner": runner,
        "provider": provider,
        "model": model,
        "cwd": cwd,
        "timeout": timeout,
        "wait": wait,
        "env": env,
        "agent_runtime_profile_id": profile_id,
        "external_workspace_id": external_workspace_id,
        "external_user_id": external_user_id,
        "external_project_id": external_project_id,
        "execution_packet": packet,
        "expected_outputs": packet["expected_outputs"],
        "approval_policy": approval_policy
        or {
            "publish": "manual",
            "external_write": "manual",
            "destructive_actions": "forbidden",
        },
        "capability_requirements": capability_requirements
        or ["filesystem", "shell", "files", "downloads"],
        "metadata": {
            **(metadata or {}),
            "build_kind": packet["build_kind"],
            "deliverable_type": packet["deliverable_type"],
        },
    }
    return {key: value for key, value in body.items() if value is not None}
