# Project Recovery User Guide

**Feature**: Soft Delete with 10-Day Recovery Window
**Version**: v3.0 (Handover 0070)
**Last Updated**: October 27, 2025

---

## Overview

GiljoAI MCP includes a project recovery system that provides a 10-day safety net for deleted projects. When you delete a project, it's not immediately removed from the database. Instead, it's hidden from view and can be recovered within 10 days.

**Key Benefits**:
- Accidental deletes can be recovered
- 10-day window to change your mind
- Self-service recovery (no admin intervention needed)
- Automatic cleanup after 10 days

---

## How It Works

### Delete Flow

When you delete a project:

1. **Confirmation Dialog**: A dialog asks you to confirm the deletion
2. **Immediate Removal**: The project disappears from all views immediately
3. **Recovery Notice**: A success modal displays with recovery instructions
4. **10-Day Window**: The project is recoverable for 10 days
5. **Automatic Purge**: After 10 days, the project is permanently deleted

### What Gets Deleted

When a project is permanently purged (after 10 days), the following are also deleted:
- All agents associated with the project
- All tasks associated with the project
- All messages associated with the project
- All agent jobs associated with the project

This is a **cascade delete** - removing the project removes everything connected to it.

---

## Deleting a Project

### Step 1: Navigate to Projects

From the dashboard, navigate to the Projects view where you can see all your projects.

### Step 2: Click the Delete Button

Click the trash icon on the project card you want to delete.

### Step 3: Confirm Deletion

A confirmation dialog will appear:

```
Delete Project 'MyProject'?

This action will hide the project from view.
You can recover it within 10 days from Settings → Database → Deleted Projects.

[Cancel]  [Delete]
```

Click **Delete** to proceed.

### Step 4: Note the Recovery Instructions

After confirming, a success modal displays:

```
✓ Project deleted from view

MyProject will be permanently purged in 10 days.

To recover before then:
Settings → Database → Deleted Projects

[OK]
```

Make note of the recovery location if you think you might need to restore the project.

---

## Recovering a Deleted Project

### Step 1: Access Settings

1. Click your avatar in the top-right corner
2. Select **Settings** from the dropdown menu

### Step 2: Navigate to Database Tab

In the Settings panel:
1. Click the **Database** tab
2. Scroll down to the **Deleted Projects** section

### Step 3: Review Deleted Projects

You'll see a table showing all deleted projects:

| Project Name | Product | Deleted Date | Purge In | Actions |
|--------------|---------|--------------|----------|---------|
| MyProject    | TinyContacts | Oct 27, 2025 | 9 days | [Restore] |
| OldTest      | TestProduct  | Oct 20, 2025 | 2 days | [Restore] |

**Column Descriptions**:
- **Project Name**: The name of the deleted project
- **Product**: The parent product the project belongs to
- **Deleted Date**: When the project was deleted
- **Purge In**: Countdown showing days remaining before permanent deletion
- **Actions**: Restore button to recover the project

### Step 4: Restore the Project

1. Click the **[Restore]** button next to the project you want to recover
2. A confirmation dialog appears:

```
Restore Project 'MyProject'?

The project will be restored as inactive.
You can activate it from the Projects view.

[Cancel]  [Restore]
```

3. Click **Restore** to proceed

### Step 5: Verify Restoration

After successful restoration:
- A success message displays: "Project restored successfully"
- The project appears back in the Projects view with status: **Inactive**
- You can now activate the project if needed

**Note**: Restored projects always return with **Inactive** status as a safety measure. This prevents conflicts with the single active project constraint (Handover 0050b).

---

## Understanding the 10-Day Window

### What Happens During the 10 Days?

**Days 1-10**:
- Project is hidden from all normal views
- Project data remains in the database
- You can restore the project at any time
- The "Purge In" countdown decreases daily

**Day 10 (End of Window)**:
- On the next application startup after day 10, the purge process runs
- Project and all associated data are permanently deleted
- No recovery is possible after this point

### When Does the Countdown Start?

The 10-day countdown starts the moment you click **Delete** on the project. The exact timestamp is recorded in the database as `deleted_at`.

### Example Timeline

```
Day 0 (Oct 27): Project deleted at 2:00 PM
Day 1-9: Project recoverable via Settings → Database
Day 10 (Nov 6): Last day to recover (until 2:00 PM)
Day 10 (after 2:00 PM): Project enters "purge eligible" state
Next Startup (Nov 7): Project permanently purged on application startup
```

---

## Common Scenarios

### Scenario 1: Accidental Delete

**Problem**: You accidentally deleted a project you're actively working on.

**Solution**:
1. Immediately go to Settings → Database → Deleted Projects
2. Find your project in the list
3. Click **[Restore]**
4. Return to Projects view and activate the project

**Time Required**: Less than 1 minute

---

### Scenario 2: Changed Your Mind

**Problem**: You deleted a project last week but now realize you need it.

**Solution**:
1. Check Settings → Database → Deleted Projects
2. Look at the "Purge In" column
3. If days remaining > 0, click **[Restore]**
4. If days remaining = 0, the project may already be purged

**Important**: Don't wait until the last day - restore as soon as you realize you need the project.

---

### Scenario 3: Product Deleted with Projects

**Problem**: You deleted a product that had projects under it.

**Behavior**:
- When you delete a product, any soft-deleted projects under that product are immediately purged
- This prevents orphaned projects from remaining in the deleted projects list
- Active projects under the product are deactivated but NOT deleted

**Best Practice**: Before deleting a product, review the deleted projects list and restore any projects you want to keep.

---

### Scenario 4: Multiple Deleted Projects

**Problem**: You have several deleted projects and want to recover only some of them.

**Solution**:
1. Go to Settings → Database → Deleted Projects
2. Review the list carefully
3. Restore only the projects you need
4. Let the others automatically purge after 10 days

**Note**: There's no bulk restore feature - you must restore projects individually.

---

## Frequently Asked Questions

### Q: Can I extend the 10-day window?

**A**: No, the 10-day window is fixed and cannot be extended. If you need more time, restore the project and then delete it again to restart the 10-day window.

---

### Q: What if I restore a project twice?

**A**: The restore operation is idempotent (safe to retry). If you click restore multiple times, only the first operation has an effect. Subsequent attempts are ignored.

---

### Q: Can I restore a project that's already active?

**A**: No. Restored projects always return with **Inactive** status. This prevents conflicts with the single active project constraint.

---

### Q: What happens if I try to delete an already deleted project?

**A**: The system will return an error: "Project already deleted". Deleted projects are hidden from normal views, so this scenario is rare.

---

### Q: Can admin users see all deleted projects across tenants?

**A**: No. Deleted projects are tenant-isolated. Each user can only see deleted projects within their own tenant.

---

### Q: Does the purge happen at a specific time?

**A**: The purge runs on application startup. If the server is restarted frequently, projects will be purged shortly after the 10-day window expires. If the server runs continuously, the purge will occur on the next restart after day 10.

---

### Q: Can I recover a project after it's been purged?

**A**: No. Once purged, the project and all associated data are permanently deleted from the database. There is no way to recover it.

---

### Q: Is there a way to permanently delete a project immediately?

**A**: No. The soft delete system is designed to provide a safety net. All deletions follow the 10-day recovery window pattern.

---

## Best Practices

### 1. Review Before Deleting

Before deleting a project:
- Review the project's agents, tasks, and messages
- Consider archiving or deactivating instead of deleting
- Remember: deletion is recoverable, but only for 10 days

### 2. Regular Cleanup

Periodically review your deleted projects:
- Go to Settings → Database → Deleted Projects
- Restore any projects you still need
- Let unwanted projects naturally purge after 10 days

### 3. Before Deleting a Product

Before deleting a product:
1. Check Settings → Database → Deleted Projects
2. Restore any soft-deleted projects under that product
3. Then delete the product

This ensures you don't lose projects unintentionally.

### 4. Recovery Notes

When you delete an important project:
- Take a screenshot of the success modal
- Note the project name and deletion date
- Set a calendar reminder for day 9 if you might want to recover it

---

## Technical Details

### Database Schema

Projects have a `deleted_at` column:
- `NULL`: Project is not deleted (normal state)
- `TIMESTAMP`: Project was deleted at this time

### Query Filtering

Deleted projects are filtered from all normal queries:
```sql
WHERE (status != 'deleted' OR deleted_at IS NULL)
```

This ensures deleted projects are invisible in:
- Projects list view
- Dashboard project counts
- API responses (except /projects/deleted endpoint)

### Purge Logic

On startup, projects where `deleted_at < NOW() - INTERVAL '10 days'` are permanently deleted.

---

## Troubleshooting

### Problem: Deleted projects not showing in recovery UI

**Possible Causes**:
1. Project was deleted more than 10 days ago (already purged)
2. Project belongs to a different tenant
3. Browser cache needs refresh

**Solution**:
1. Refresh the page (Ctrl+R or Cmd+R)
2. Verify you're logged into the correct tenant
3. Check if the 10-day window has expired

---

### Problem: Restore button not working

**Possible Causes**:
1. Network connectivity issue
2. Concurrent restore attempt
3. Project already restored by another user

**Solution**:
1. Check browser console for errors (F12)
2. Refresh the page and try again
3. Verify the project isn't already in the Projects view

---

### Problem: Purge countdown showing negative days

**Possible Causes**:
1. Application hasn't been restarted since day 10
2. Display bug in the UI

**Solution**:
1. Restore the project immediately if you need it
2. On next application restart, the project will be purged
3. Report the UI bug if countdown shows negative numbers

---

## Summary

The project recovery system provides a 10-day safety net for deleted projects, giving you peace of mind while maintaining a clean database through automatic purging.

**Key Takeaways**:
- Deleted projects are recoverable for 10 days
- Recovery UI is in Settings → Database → Deleted Projects
- Restored projects return as Inactive
- Automatic purge after 10 days (on startup)
- Multi-tenant isolation maintained throughout

**Need Help?**

If you encounter issues with project recovery, check:
1. This user guide for common scenarios
2. The system logs for error messages
3. The GitHub issues page for known bugs

---

**Document Version**: 1.0
**Feature Version**: v3.0 (Handover 0070)
**Last Updated**: October 27, 2025
