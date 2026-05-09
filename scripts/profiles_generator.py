import yaml
import argparse
from pathlib import Path
from copy import deepcopy


def merge_dict(base_dict, override_dict):
    result = deepcopy(base_dict)
    for k, v in (override_dict or {}).items():
        result[k] = v
    return result


def build_quality_list(quality_order, quality_map, upto_name):
    idx = quality_order.index(upto_name)
    selected = quality_order[idx:]

    result = []
    for name in selected:
        qdef = deepcopy(quality_map[name])
        result.append(qdef)
    return result


def build_custom_formats(base_cf, variant_cf):
    merged = merge_dict(base_cf, variant_cf)
    return [
        {"name": name, "score": score}
        for name, score in sorted(merged.items(), key=lambda x: x[1], reverse=True)
    ]


def generate_profiles(definition_path, profile_definitions_path, output_dir):
    # Load files
    with open(definition_path) as f:
        definition = yaml.safe_load(f)

    with open(profile_definitions_path) as f:
        profile_defs = yaml.safe_load(f)

    base = definition["base_profile"]
    quality_order = definition["quality_order"]
    variants = definition["variants"]

    # Map quality name -> full definition
    quality_map = {q["name"]: q for q in profile_defs["qualities"]}

    for variant_name, variant_data in variants.items():
        for quality_name in quality_order:
            # Base profile structure
            profile = {
                "name": f"{quality_name} {variant_name}",
                "description": f"This profile allows quality up to {quality_name}.",
                "tags": [variant_name, quality_name],
            }

            # Merge base profile
            profile = merge_dict(profile, base)

            # Custom formats (base + variant)
            profile["custom_formats"] = build_custom_formats(
                base.get("custom_formats", {}),
                variant_data.get("custom_formats", {})
            )

            # Build quality list
            profile["qualities"] = build_quality_list(
                quality_order,
                quality_map,
                quality_name
            )

            # Upgrade until logic
            if profile.get("upgradesAllowed", False):
                quality_data = quality_map[quality_name]
                profile["upgrade_until"] = {
                    "id": quality_data["id"],
                    "name": quality_data["name"],
                }

            # Full override from variant
            profile = merge_dict(profile, variant_data.get("override", {}))

            # Output file
            filename = Path(output_dir, f"{profile['name']}.yml")
            filename.parent.mkdir(parents=True, exist_ok=True)

            with open(filename, "w") as f:
                yaml.dump(profile, f, sort_keys=False)


def main():
    parser = argparse.ArgumentParser(description="Generate Sonarr/Profilarr profiles from templates")

    parser.add_argument(
        "-d", "--definition",
        default="templates/definition.yml",
        help="Path to definition.yml"
    )

    parser.add_argument(
        "-p", "--profile-definitions",
        default="templates/profile-definitions.yml",
        help="Path to profile-definitions.yml"
    )

    parser.add_argument(
        "-o", "--output",
        default="profiles",
        help="Output directory for generated profiles"
    )

    args = parser.parse_args()

    generate_profiles(
        definition_path=args.definition,
        profile_definitions_path=args.profile_definitions,
        output_dir=args.output
    )

    print(f"Profiles generated in ./{args.output}/")


if __name__ == "__main__":
    main()
