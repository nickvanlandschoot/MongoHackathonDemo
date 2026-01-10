"""
Backfill maintainer information into existing dependency trees.
"""
import requests
from database import get_database, get_database_manager

def fetch_maintainers_from_npm(package_name: str) -> list:
    """Fetch maintainers for a package from npm registry."""
    try:
        url = f"https://registry.npmjs.org/{package_name}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "maintainers" in data and isinstance(data["maintainers"], list):
                return [m.get("name") for m in data["maintainers"] if m.get("name")]
    except Exception as e:
        print(f"  ✗ Error fetching {package_name}: {e}")
    return []

def add_maintainers_to_node(node: dict, indent: str = "") -> dict:
    """
    Recursively add maintainer information to a dependency node.
    """
    if not isinstance(node, dict):
        return node

    # If this node has a name, fetch its maintainers
    if "name" in node and "maintainers" not in node:
        package_name = node["name"]
        maintainers = fetch_maintainers_from_npm(package_name)
        node["maintainers"] = maintainers
        print(f"{indent}✓ {package_name}: {len(maintainers)} maintainers")

    # Recursively process children
    for dep_type in ["dependencies", "devDependencies", "optionalDependencies", "peerDependencies"]:
        if dep_type in node and isinstance(node[dep_type], dict):
            for dep_name, dep_data in node[dep_type].items():
                if "children" in dep_data and isinstance(dep_data["children"], dict):
                    add_maintainers_to_node(dep_data["children"], indent + "  ")

    return node

def main():
    # Connect to database
    db_manager = get_database_manager()
    db_manager.connect()

    db = get_database()

    # Get all dependency trees
    trees = list(db.dependency_trees.find({}))

    print(f"\n{'='*60}")
    print(f"BACKFILLING MAINTAINER DATA IN DEPENDENCY TREES")
    print(f"{'='*60}\n")
    print(f"Found {len(trees)} dependency trees\n")

    for tree in trees:
        tree_name = tree.get("name")
        tree_version = tree.get("version")
        print(f"\nProcessing: {tree_name}@{tree_version}")
        print(f"{'='*40}")

        # Add maintainers to root level
        if "maintainers" not in tree:
            maintainers = fetch_maintainers_from_npm(tree_name)
            tree["maintainers"] = maintainers
            print(f"Root: {len(maintainers)} maintainers")

        # Process all dependency types
        for dep_type in ["dependencies", "devDependencies", "optionalDependencies", "peerDependencies"]:
            if dep_type in tree and isinstance(tree[dep_type], dict):
                print(f"\n{dep_type}:")
                for dep_name, dep_data in tree[dep_type].items():
                    if "children" in dep_data and isinstance(dep_data["children"], dict):
                        add_maintainers_to_node(dep_data["children"], "  ")

        # Update the tree in database
        db.dependency_trees.update_one(
            {"_id": tree["_id"]},
            {"$set": tree}
        )
        print(f"\n✓ Updated {tree_name}@{tree_version} in database")

    print(f"\n{'='*60}")
    print(f"COMPLETE")
    print(f"{'='*60}\n")

    # Disconnect from database
    db_manager.disconnect()

if __name__ == "__main__":
    main()
