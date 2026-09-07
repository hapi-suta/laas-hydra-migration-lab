# Find the orphaned resources

After teardown, inspect why AWS may still show storage charges for your practice name.

Check retained final snapshots, scheduled-deletion secrets, CloudWatch log retention, manually created DMS objects, and any failed resource deletion. Distinguish deliberate retention from a forgotten running service.

Do not remove shared resources or force-delete retained snapshots merely to make the bill disappear. Follow the agreed retention policy, then document the exact remaining cost sources and scheduled cleanup.

**Success:** no unintended running practice compute, retained data accounted for, and a clear owner for final cleanup.
