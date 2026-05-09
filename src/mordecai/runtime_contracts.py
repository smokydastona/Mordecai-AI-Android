from __future__ import annotations

import argparse
import json
from pathlib import Path

from mordecai_core.runtime import RuntimeComponents, get_runtime_components


CONTRACT_VERSION = 1


def provider_registry_snapshot(components: RuntimeComponents) -> dict[str, object]:
    settings = components.runtime.settings
    preferred_provider = components.runtime.provider_router.preferred_provider_name()
    providers: list[dict[str, object]] = []
    capabilities_matrix = components.provider_catalog.capabilities_matrix()
    for provider_name in components.provider_catalog.names():
        capabilities = capabilities_matrix[provider_name]
        providers.append(
            {
                "name": provider_name,
                "integration_type": "local" if capabilities["local"] else "remote",
                "local": capabilities["local"],
                "streaming": capabilities["streaming"],
                "vision": capabilities["vision"],
                "tool_calling": capabilities["tool_calling"],
                "max_context": capabilities["max_context"],
                "preferred": provider_name == preferred_provider,
                "configured_default": provider_name == settings.default_provider,
            }
        )
    return {
        "contract": "provider-registry",
        "version": CONTRACT_VERSION,
        "mode": settings.mode,
        "configured_default_provider": settings.default_provider,
        "preferred_provider": preferred_provider,
        "providers": providers,
    }


def tool_manifest_snapshot(components: RuntimeComponents) -> dict[str, object]:
    settings = components.runtime.settings
    tools = components.tool_registry.capability_manifest()
    return {
        "contract": "tool-manifest",
        "version": CONTRACT_VERSION,
        "mode": settings.mode,
        "tool_count": len(tools),
        "tools": tools,
    }


def export_runtime_contracts(output_dir: Path, components: RuntimeComponents | None = None) -> dict[str, str]:
    components = components or get_runtime_components()
    output_dir.mkdir(parents=True, exist_ok=True)

    provider_registry_path = output_dir / "provider-registry.json"
    tool_manifest_path = output_dir / "tool-manifest.json"

    provider_registry_path.write_text(
        json.dumps(provider_registry_snapshot(components), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tool_manifest_path.write_text(
        json.dumps(tool_manifest_snapshot(components), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return {
        "provider_registry": provider_registry_path.as_posix(),
        "tool_manifest": tool_manifest_path.as_posix(),
    }


def main(argv: list[str] | None = None) -> int:
    components = get_runtime_components()
    parser = argparse.ArgumentParser(description="Export Mordecai runtime provider and tool contracts.")
    parser.add_argument(
        "--export-dir",
        default=str(components.runtime.settings.state_dir / "contracts"),
        help="Directory where provider-registry.json and tool-manifest.json will be written.",
    )
    args = parser.parse_args(argv)

    exported = export_runtime_contracts(Path(args.export_dir), components)
    print(json.dumps(exported, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())