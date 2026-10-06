"""
DataGuard Review Proposed Fixes

Lets a human list pending items in the proposed_fixes queue, and mark
each one approved or rejected. Nothing in this script ever modifies
clean_311_requests or any source data -- it only changes the status of
a review queue entry. Actually applying an approved fix to real data
(moving status from 'approved' to 'applied') is a separate, deliberately
unbuilt step: none of DataGuard's current quality rules represent a
fix that's safe to apply without further, rule-specific logic, so this
script stops at recording the human decision.

Usage:
    python review_proposed_fixes.py --list
    python review_proposed_fixes.py --fix-id 3 --approve --reviewer "Sameeksha"
    python review_proposed_fixes.py --fix-id 3 --reject --reviewer "Sameeksha"
"""

import argparse

from db_utils import get_postgres_connection


def list_pending_fixes(cursor):
    """Returns every proposed_fixes row still awaiting a human decision."""
    cursor.execute(
        """
        SELECT fix_id, rule_code, ai_severity, ai_action,
               array_length(affected_unique_keys, 1) AS affected_count,
               proposed_change, created_at
        FROM proposed_fixes
        WHERE status = 'pending_review'
        ORDER BY created_at ASC;
        """
    )
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def update_fix_status(cursor, fix_id, new_status, reviewed_by):
    """
    Updates a proposed_fixes row's status, but only if it is currently
    still 'pending_review' -- this prevents accidentally re-reviewing a
    fix that was already decided. Returns the updated row if the update
    actually applied, or None if fix_id didn't exist or wasn't pending.
    """
    cursor.execute(
        """
        UPDATE proposed_fixes
        SET status = %s,
            reviewed_by = %s,
            reviewed_at = CURRENT_TIMESTAMP
        WHERE fix_id = %s
          AND status = 'pending_review'
        RETURNING fix_id, rule_code, status;
        """,
        (new_status, reviewed_by, fix_id),
    )
    row = cursor.fetchone()
    if row is None:
        return None

    columns = [description[0] for description in cursor.description]
    return dict(zip(columns, row))


def print_pending_fixes(pending_fixes):
    """Prints a readable summary of pending fixes."""
    if not pending_fixes:
        print("No fixes are currently pending review.")
        return

    print(f"\n{len(pending_fixes)} fix(es) pending review:\n")
    for fix in pending_fixes:
        print(f"  fix_id {fix['fix_id']}: {fix['rule_code']}")
        print(f"    severity: {fix['ai_severity']}, action: {fix['ai_action']}")
        print(f"    affected records: {fix['affected_count']}")
        print(f"    proposed change: {fix['proposed_change']}")
        print(f"    created: {fix['created_at']}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="List or decide on items in the proposed_fixes human-review queue."
    )
    parser.add_argument("--list", action="store_true", help="List all pending fixes.")
    parser.add_argument("--fix-id", type=int, default=None, help="The fix_id to approve or reject.")
    parser.add_argument("--approve", action="store_true", help="Mark the given fix_id as approved.")
    parser.add_argument("--reject", action="store_true", help="Mark the given fix_id as rejected.")
    parser.add_argument("--reviewer", default=None, help="Name of the person making this decision.")
    args = parser.parse_args()

    if args.approve and args.reject:
        parser.error("Use either --approve or --reject, not both.")

    if (args.approve or args.reject) and (args.fix_id is None or not args.reviewer):
        parser.error("--approve/--reject require both --fix-id and --reviewer.")

    connection = None
    try:
        connection = get_postgres_connection()

        with connection.cursor() as cursor:
            if args.list or not (args.approve or args.reject):
                pending_fixes = list_pending_fixes(cursor)
                print_pending_fixes(pending_fixes)
                return

            new_status = "approved" if args.approve else "rejected"
            updated = update_fix_status(cursor, args.fix_id, new_status, args.reviewer)

            if updated is None:
                print(
                    f"No pending fix found with fix_id {args.fix_id}. "
                    f"It may not exist, or may have already been reviewed."
                )
                return

            connection.commit()
            print(f"fix_id {updated['fix_id']} ({updated['rule_code']}) marked as {updated['status']}.")

    finally:
        if connection:
            connection.close()


if __name__ == "__main__":
    main()