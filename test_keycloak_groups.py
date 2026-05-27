#!/usr/bin/env python3
"""
Test script to verify that all Keycloak groups are being fetched correctly.
This script tests the paginated group fetching implementation.
"""

import os
import sys
from githubapp.keycloak import Keycloak

def test_list_groups():
    """Test the list_groups method to ensure it fetches all teams."""
    try:
        print("=" * 60)
        print("Testing Keycloak Group Fetching with Pagination")
        print("=" * 60)

        # Initialize Keycloak client
        keycloak = Keycloak()

        # Fetch all groups
        print("\nFetching all groups from Keycloak...")
        groups = keycloak.list_groups()

        # Display results
        print("\n" + "=" * 60)
        print(f"RESULTS: Found {len(groups)} total groups")
        print("=" * 60)

        if groups:
            print("\nList of all groups:")
            for i, group in enumerate(sorted(groups), 1):
                print(f"  {i:3d}. {group}")
        else:
            print("\nNo groups found. Please check:")
            print("  1. KEYCLOAK_PARENT_GROUP_ID environment variable is set")
            print("  2. Keycloak connection settings are correct")
            print("  3. The parent group has subgroups")

        # Check if we got the expected number of groups
        parent_group_id = os.environ.get("KEYCLOAK_PARENT_GROUP_ID")
        if parent_group_id:
            print(f"\nParent Group ID: {parent_group_id}")

            # Also try to get the parent group info to see the expected count
            try:
                parent_group = keycloak.client.get_group(parent_group_id)
                expected_count = parent_group.get("subGroupCount", 0)
                print(f"Expected subgroup count from parent: {expected_count}")

                if len(groups) < expected_count:
                    print(f"\n⚠️  WARNING: Found {len(groups)} groups but expected {expected_count}")
                    print("Some groups may not have been fetched correctly.")
                elif len(groups) >= expected_count:
                    print(f"\n✅ SUCCESS: Fetched all or more groups than the direct subgroup count")
                    print("(This is expected if there are nested subgroups)")
            except Exception as e:
                print(f"\nCouldn't fetch parent group info: {e}")

        return groups

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    groups = test_list_groups()

    # Exit with status code based on results
    if len(groups) >= 30:  # Expecting at least 30+ groups based on the 39 subGroupCount
        print("\n✅ Test PASSED: Successfully fetched a large number of groups")
        sys.exit(0)
    else:
        print(f"\n❌ Test FAILED: Only fetched {len(groups)} groups")
        sys.exit(1)